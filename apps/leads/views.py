# apps/leads/views.py

from rest_framework import viewsets, permissions, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from .models import Lead
from .serializers import LeadSerializer
from .permissions import IsOwnerOrAssignedOrAdmin, IsAdminOrManagerUser
from .pagination import StandardResultsSetPagination
from django.utils import timezone
from datetime import timedelta
from rest_framework.parsers import MultiPartParser
import pandas as pd
from io import StringIO
from django.http import HttpResponse
from dateutil.relativedelta import relativedelta
from django.db.models import Count, Sum, F, Case, When, FloatField, IntegerField, Q, Value, Func, functions
from django.db.models.functions import Coalesce, Cast, TruncMonth, TruncDate, TruncDay, Greatest
from decimal import Decimal 
from django.contrib.auth import get_user_model
from apps.property.models import Property

User = get_user_model()

class NullIfEmpty(Func):
    function = 'NULLIF'
    template = "%(function)s(%(expressions)s, '')"

class LeadViewSet(viewsets.ModelViewSet):
    serializer_class = LeadSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrAssignedOrAdmin]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'source', 'priority', 'assigned_to', 'created_by']
    search_fields = ['name', 'email', 'phone', 'company', 'interest']
    ordering_fields = ['created_at', 'updated_at', 'name', 'status', 'priority']
    ordering = ['-created_at']

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser or getattr(user, 'role', None) in ['admin', 'manager']:
            return Lead.objects.all().select_related('assigned_to', 'created_by')
        else:
            return Lead.objects.filter(assigned_to=user).select_related('assigned_to', 'created_by')

    def get_permissions(self):
        if self.action in ['import_leads', 'export_leads', 'dashboard_stats', 'revenue_overview']:
            return [permissions.IsAuthenticated(), IsAdminOrManagerUser()]
        return [permission() for permission in self.permission_classes]

    @action(detail=False, methods=['get'])
    def team_performance(self, request):
        """
        Get team performance metrics including:
        - Number of leads handled
        - Conversion rate
        - Total revenue from converted leads
        - Performance trend
        """
        try:
            # Get the last 30 days of data
            thirty_days_ago = timezone.now() - timedelta(days=30)
            
            # Check if we have any users with role='agent'
            agent_count = User.objects.filter(role__iexact='agent').count()
            print(f"Found {agent_count} users with role='agent'")
            
            # Get all available roles for debugging
            available_roles = User.objects.values_list('role', flat=True).distinct()
            print(f"Available roles in the database: {list(available_roles)}")

            # Check if the assigned_leads relationship exists
            user_model_fields = [f.name for f in User._meta.get_fields()]
            if 'assigned_leads' not in user_model_fields:
                print("Error: 'assigned_leads' relationship not found in User model")
                return Response(
                    {'error': 'User model is missing assigned_leads relationship'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            
            # Get agents and their performance metrics with safe aggregations
            team_stats = User.objects.filter(
                role__iexact='agent'  # Case-insensitive match
            ).annotate(
                total_leads=Coalesce(Count('assigned_leads'), 0),
                converted_leads=Coalesce(Count('assigned_leads', filter=Q(assigned_leads__status='Converted')), 0),
                conversion_rate=Case(
                    When(total_leads=0, then=Value(0.0)),
                    default=Cast(
                        Cast(F('converted_leads'), FloatField()) * 100.0 / 
                        Cast(F('total_leads'), FloatField()),
                        output_field=FloatField()
                    ),
                ),
                
                # Handle budget field with robust validation
                clean_budget=Case(
                    When(
                        Q(assigned_leads__budget='') | 
                        Q(assigned_leads__budget__isnull=True),
                        then=Value(0.0)
                    ),
                    When(
                        Q(assigned_leads__budget__regex=r'^[^0-9.-]'),  # Non-numeric values
                        then=Value(0.0)
                    ),
                    default=Case(
                        When(
                            Q(assigned_leads__budget__regex=r'^-?\d*\.?\d*$'),  # Valid number
                            then=functions.Greatest(
                                Cast(F('assigned_leads__budget'), output_field=FloatField()),
                                Value(0.0)
                            )
                        ),
                        default=Value(0.0),
                        output_field=FloatField(),
                    ),
                    output_field=FloatField(),
                ),
                
                # Calculate revenue only from converted leads with improved validation
                revenue=Coalesce(
                    Sum(
                        Case(
                            When(
                                Q(assigned_leads__status='Converted') &
                                ~Q(assigned_leads__budget='') &
                                ~Q(assigned_leads__budget__isnull=True) &
                                Q(assigned_leads__budget__regex=r'^-?\d*\.?\d*$'),  # Valid number format
                                then=functions.Greatest(
                                    Cast('clean_budget', output_field=FloatField()),
                                    Value(0.0)
                                )
                            ),
                            default=Value(0.0),
                            output_field=FloatField(),
                        )
                    ),
                    Value(0.0),
                    output_field=FloatField()
                ),
            ).values(
                'id', 
                'first_name', 
                'last_name', 
                'username',
                'profile_image',
                'total_leads',
                'converted_leads',
                'conversion_rate',
                'revenue'
            )

            # Print the raw query for debugging
            print(f"Generated query: {str(team_stats.query)}")
            print(f"Found {len(team_stats)} agents with stats")

            # Format the data with additional error handling
            formatted_stats = []
            for stat in team_stats:
                try:
                    name = f"{stat.get('first_name') or ''} {stat.get('last_name') or ''}".strip() or stat.get('username', '')
                    avatar_url = None
                    if stat.get('profile_image'):
                        try:
                            avatar_url = request.build_absolute_uri(stat['profile_image'])
                        except Exception as e:
                            print(f"Error building avatar URL for user {name}: {str(e)}")
                    
                    formatted_stats.append({
                        'agent': name,
                        'avatar': avatar_url,
                        'deals': stat.get('converted_leads', 0),
                        'conversion_rate': round(float(stat.get('conversion_rate', 0) or 0), 1),
                        'revenue': int(round(float(stat.get('revenue', 0) or 0))),
                        'total_leads': stat.get('total_leads', 0)
                    })
                except Exception as e:
                    print(f"Error formatting stats for user: {str(e)}")
                    continue

            # Sort by revenue descending
            formatted_stats.sort(key=lambda x: x['revenue'], reverse=True)
            
            print(f"Returning {len(formatted_stats)} formatted agent stats")
            return Response(formatted_stats)
            
        except Exception as e:
            import traceback
            print(f"Error in team_performance endpoint: {str(e)}")
            print(traceback.format_exc())
            return Response(
                {'error': 'An error occurred while fetching team performance data'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def revenue_overview(self, request):
        """
        Calculates total revenue and sales commission from converted leads, grouped by period.
        - Supports daily or monthly grouping based on time range
        - Handles missing periods with zero values
        - Sales commission is calculated as 60% of revenue
        - Improved budget validation and handling
        """
        try:
            time_range = request.query_params.get('time_range', 'year')
            now = timezone.now()
            start_date = now
            group_by_day = False
            date_format = '%b %Y'  # Default monthly format

            # Determine time range and grouping
            if time_range == 'this_month':
                start_date = now.replace(day=1, hour=0, minute=0, second=0)
                group_by_day = True
                date_format = '%b %d'
            elif time_range == '3_months':
                start_date = now - relativedelta(months=3)
                group_by_day = True
                date_format = '%b %d'
            elif time_range == '6_months':
                start_date = now - relativedelta(months=6)
            else:  # Default to 1 year
                start_date = now - relativedelta(years=1)

            # Query converted leads with improved budget validation
            queryset = Lead.objects.filter(
                status='Converted',
                updated_at__gte=start_date
            )

            # Use TruncDay or TruncMonth based on grouping type
            trunc_period = TruncDay('updated_at') if group_by_day else TruncMonth('updated_at')

            # Calculate revenue with robust budget handling
            revenue_by_period = queryset.annotate(
                period=trunc_period,
                clean_budget=Case(
                    When(
                        Q(budget='') | Q(budget__isnull=True),
                        then=Value(0.0)
                    ),
                    When(
                        Q(budget__regex=r'^[^0-9.-]'),  # Non-numeric values
                        then=Value(0.0)
                    ),
                    default=Case(
                        When(
                            Q(budget__regex=r'^-?\d*\.?\d*$'),  # Valid number
                            then=functions.Greatest(
                                Cast('budget', output_field=FloatField()),
                                Value(0.0)
                            )
                        ),
                        default=Value(0.0),
                        output_field=FloatField(),
                    ),
                    output_field=FloatField(),
                )
            ).values('period').annotate(
                total_revenue=Sum('clean_budget')
            ).values('period', 'total_revenue').order_by('period')

            # Generate all periods in range for consistent data points
            all_periods = []
            current = start_date
            end_date = now.replace(hour=23, minute=59, second=59)  # Include full current day

            while current <= end_date:
                period = current.replace(hour=0, minute=0, second=0, microsecond=0)
                if group_by_day:
                    all_periods.append(period)
                    current += timedelta(days=1)
                else:
                    all_periods.append(period.replace(day=1))  # First day of month for monthly grouping
                    current += relativedelta(months=1)
                    current = current.replace(day=1)

            # Create lookup table for existing data
            existing_data = {
                item['period'].replace(hour=0, minute=0, second=0, microsecond=0): item['total_revenue'] or 0.0
                for item in revenue_by_period
            }

            # Format response with all periods and calculated values
            formatted_data = []
            for period in all_periods:
                revenue = float(existing_data.get(period, 0.0))
                sales_commission = round(revenue * 0.6, 2)  # 60% commission rate
                
                formatted_data.append({
                    "name": period.strftime(date_format),
                    "revenue": round(revenue, 2),
                    "sales": sales_commission
                })

            return Response(formatted_data)
            
        except Exception as e:
            print(f"Error in revenue_overview endpoint: {str(e)}")
            return Response(
                {'error': 'An error occurred while processing revenue data'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
    @action(detail=False, methods=['get'])
    def dashboard_stats(self, request):
        # ... (The rest of your code remains the same)
        queryset = self.filter_queryset(self.get_queryset())
        now = timezone.now()
        
        current_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        previous_month_end = current_month_start - timedelta(days=1)
        previous_month_start = previous_month_end.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        current_month_queryset = queryset.filter(created_at__gte=current_month_start)
        previous_month_queryset = queryset.filter(created_at__gte=previous_month_start, created_at__lt=current_month_start)

        time_range = request.query_params.get('time_range', 'week')
        today = now.date()
        if time_range == 'year':
            start_date = today - timedelta(days=364)
        elif time_range == 'month':
            start_date = today - timedelta(days=29)
        else:
            start_date = today - timedelta(days=6)

        daily_leads_data = queryset.filter(created_at__date__gte=start_date)\
                                   .annotate(date=TruncDate('created_at'))\
                                   .values('date')\
                                   .annotate(count=Count('id'))\
                                   .order_by('date')
        
        counts_by_date = {item['date'].strftime('%Y-%m-%d'): item['count'] for item in daily_leads_data}
        all_dates_in_range = [start_date + timedelta(days=i) for i in range((today - start_date).days + 1)]
        formatted_daily_leads = [{'date': dt.strftime('%Y-%m-%d'), 'count': counts_by_date.get(dt.strftime('%Y-%m-%d'), 0)} for dt in all_dates_in_range]

        overall_total_leads = queryset.count()
        overall_converted_leads = queryset.filter(status='Converted').count()

        return Response({
            'total_leads': overall_total_leads,
            'converted_leads': overall_converted_leads,
            'new_leads': queryset.filter(status='New').count(), 
            'qualified_leads': queryset.filter(status='Qualified').count(), 
            'conversion_rate': round((overall_converted_leads / overall_total_leads * 100) if overall_total_leads > 0 else 0, 1),
            'current_month_total_leads': current_month_queryset.count(),
            'current_month_converted_leads': current_month_queryset.filter(status='Converted').count(),
            'current_month_new_leads': current_month_queryset.filter(status='New').count(),
            'current_month_qualified_leads': current_month_queryset.filter(status='Qualified').count(),
            'previous_month_total_leads': previous_month_queryset.count(),
            'previous_month_converted_leads': previous_month_queryset.filter(status='Converted').count(),
            'previous_month_new_leads': previous_month_queryset.filter(status='New').count(),
            'previous_month_qualified_leads': previous_month_queryset.filter(status='Qualified').count(),
            'status_distribution': list(queryset.values('status').annotate(count=Count('status')).order_by('status')),
            'source_distribution': list(queryset.values('source').annotate(count=Count('source')).order_by('source')),
            'recent_leads': LeadSerializer(queryset.order_by('-created_at')[:5], many=True, context={'request': request}).data,
            'daily_leads_added': formatted_daily_leads,
        })
        
    @action(detail=False, methods=['post'], parser_classes=[MultiPartParser])
    def import_leads(self, request):
        if 'file' not in request.FILES:
            return Response({'error': 'No file provided'}, status=status.HTTP_400_BAD_REQUEST)
        
        file = request.FILES['file']
        file_name_lower = file.name.lower()

        if not file_name_lower.endswith(('.csv', '.xlsx', '.xls')):
            return Response(
                {'error': 'Unsupported file format. Please use CSV, XLSX, or XLS.'},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        try:
            if file_name_lower.endswith('.csv'):
                try:
                    # For CSV, ensure it's read as a string initially to avoid type issues
                    df = pd.read_csv(file, dtype=str, keep_default_na=False, na_filter=False)
                except UnicodeDecodeError:
                    file.seek(0)
                    df = pd.read_csv(file, encoding='latin1', dtype=str, keep_default_na=False, na_filter=False)
            elif file_name_lower.endswith('.xlsx'):
                try:
                    # Explicitly use openpyxl for .xlsx
                    # Ensure all data is read as string to prevent pandas from inferring types like int/float for phone numbers etc.
                    df = pd.read_excel(file, engine='openpyxl', dtype=str, keep_default_na=False, na_filter=False)
                except ImportError:
                    return Response(
                        {'error': "Processing .xlsx files requires the 'openpyxl' library. Please install it (`pip install openpyxl`) and try again."},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR # Or 400 if you consider it a client-side setup issue
                    )
                except Exception as e: # Catch other potential errors from read_excel
                    return Response(
                        {'error': f"Error reading XLSX file: {str(e)}"},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            elif file_name_lower.endswith('.xls'):
                try:
                    # Explicitly use xlrd for .xls
                    df = pd.read_excel(file, engine='xlrd', dtype=str, keep_default_na=False, na_filter=False)
                except ImportError:
                    return Response(
                        {'error': "Processing .xls files requires the 'xlrd' library. Please install it (`pip install xlrd`) and try again."},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR # Or 400
                    )
                except Exception as e: # Catch other potential errors from read_excel
                     return Response(
                        {'error': f"Error reading XLS file: {str(e)}"},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            else: # Should not be reached due to earlier check, but as a safeguard
                return Response(
                    {'error': 'Internal error: Unsupported file format processing.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            df.columns = [str(col).strip().lower() for col in df.columns] # Ensure column names are strings before stripping
            
            created_count = 0
            skipped_rows_details = []

            expected_columns = [
                'name', 'email', 'phone', 'status', 'source', 'interest', 
                'priority', 'company', 'position', 'budget', 'timeline', 
                'requirements', 'notes', 'tags'
            ]
            
            # Basic check if essential columns are present (optional, but good for robustness)
            # For a more robust solution, you'd check if ALL required columns are present.
            if 'name' not in df.columns or 'email' not in df.columns or 'phone' not in df.columns:
                 return Response(
                    {'error': 'Missing essential columns in the file. Required columns include at least: name, email, phone.'},
                    status=status.HTTP_400_BAD_REQUEST
                )


            for index, row in df.iterrows():
                lead_data = {
                    'name': row.get('name', '').strip(),
                    'email': row.get('email', '').strip(),
                    'phone': str(row.get('phone', '')).strip(), # Ensure phone is treated as string
                    'status': row.get('status', 'New').strip(),
                    'source': row.get('source', 'Website').strip(),
                    'interest': row.get('interest', '').strip(),
                    'priority': row.get('priority', 'Medium').strip(),
                    'company': row.get('company', '').strip(),
                    'position': row.get('position', '').strip(),
                    'budget': str(row.get('budget', '')).strip(), # Ensure budget is string
                    'timeline': row.get('timeline', '').strip(),
                    'requirements': row.get('requirements', '').strip(),
                    'notes': row.get('notes', '').strip(),
                    # Ensure tags are handled as a list of strings
                    'tags': [tag.strip() for tag in str(row.get('tags', '')).split(',') if tag.strip()] if pd.notna(row.get('tags')) and str(row.get('tags', '')).strip() else [],
                }
                
                # Validate required fields like name, email, phone
                if not lead_data['name'] or not lead_data['email'] or not lead_data['phone']:
                    skipped_rows_details.append({
                        'row_number': index + 2, # +2 because index is 0-based and header is row 1
                        'errors': {'Required fields': ['Name, Email, and Phone are mandatory.']}
                    })
                    continue

                serializer = LeadSerializer(data=lead_data, context={'request': request})
                if serializer.is_valid():
                    # Assign to the importing user by default, or allow override if 'assigned_to_email' or 'assigned_to_id' is in the file
                    # For simplicity, we'll assign to the current user.
                    # More complex logic could involve looking up users by email/ID from the file.
                    serializer.save(assigned_to=request.user) # Explicitly assign to current user
                    created_count += 1
                else:
                    skipped_rows_details.append({'row_number': index + 2, 'errors': serializer.errors})
            
            message = f'{created_count} leads imported successfully.'
            response_status = status.HTTP_201_CREATED

            if skipped_rows_details:
                message += f' {len(skipped_rows_details)} rows were skipped.'
                if created_count == 0 and skipped_rows_details: # If all rows failed
                    response_status = status.HTTP_400_BAD_REQUEST
                # If some succeeded and some failed, it's still partially successful (207 Multi-Status could be used too)
                # For simplicity, we'll use 201 if any were created, or 400 if none were and there were skips.

            return Response(
                {'message': message, 'created_count': created_count, 'skipped_count': len(skipped_rows_details), 'skipped_details': skipped_rows_details if skipped_rows_details else None},
                status=response_status
            )
            
        except pd.errors.EmptyDataError:
            return Response({'error': 'The uploaded file is empty or not a valid CSV/Excel file.'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            # Log the full error for debugging on the server
            print(f"Critical error during lead import: {str(e)}")
            import traceback
            traceback.print_exc() # This will print the full traceback to your server logs
            return Response(
                {'error': 'An unexpected critical error occurred during import. Please check server logs.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


    @action(detail=False, methods=['get'])
    def export(self, request):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = LeadSerializer(queryset, many=True, context={'request': request})
        data_to_export = []

        for lead_data in serializer.data:
            flat_lead = lead_data.copy()
            if 'assigned_to_detail' in flat_lead and flat_lead['assigned_to_detail']:
                flat_lead['assigned_to_name'] = f"{flat_lead['assigned_to_detail'].get('first_name','')} {flat_lead['assigned_to_detail'].get('last_name','')}".strip()
                flat_lead['assigned_to_email'] = flat_lead['assigned_to_detail'].get('email','')
            else:
                flat_lead['assigned_to_name'] = 'Unassigned'
                flat_lead['assigned_to_email'] = ''
            if 'assigned_to_detail' in flat_lead: del flat_lead['assigned_to_detail']
            
            if 'created_by_detail' in flat_lead and flat_lead['created_by_detail']:
                 flat_lead['created_by_name'] = f"{flat_lead['created_by_detail'].get('first_name','')} {flat_lead['created_by_detail'].get('last_name','')}".strip()
                 flat_lead['created_by_email'] = flat_lead['created_by_detail'].get('email','') # Assuming email is available
            else:
                flat_lead['created_by_name'] = ''
                flat_lead['created_by_email'] = ''
            if 'created_by_detail' in flat_lead: del flat_lead['created_by_detail']

            if isinstance(flat_lead.get('tags'), list):
                flat_lead['tags'] = ','.join(flat_lead['tags'])
            
            # Ensure all fields from the model are present, even if empty, for consistent CSV columns
            # This list should ideally match your model fields or desired export columns
            all_model_fields = [f.name for f in Lead._meta.get_fields() if not f.is_relation or f.one_to_one or (f.many_to_one and f.related_model)]
            # Add custom fields from serializer
            custom_fields = ['assigned_to_name', 'assigned_to_email', 'created_by_name', 'created_by_email']
            
            output_row = {}
            for field_name in all_model_fields + custom_fields:
                output_row[field_name] = flat_lead.get(field_name, '')
            
            # Remove fields we don't want to export directly if they were part of all_model_fields
            # e.g., 'assigned_to', 'created_by' (IDs) if you only want names/emails
            if 'assigned_to' in output_row: del output_row['assigned_to']
            if 'created_by' in output_row: del output_row['created_by']


            data_to_export.append(output_row)

        df = pd.DataFrame(data_to_export)
        
        # Define a specific order for columns if desired
        # ordered_columns = ['id', 'name', 'email', 'phone', 'company', 'position', 'status', 'source', 'interest', 'priority', 
        #                    'assigned_to_name', 'assigned_to_email', 'budget', 'timeline', 'requirements', 'notes', 'tags',
        #                    'created_by_name', 'created_by_email', 'created_at', 'updated_at', 'last_activity']
        # df = df.reindex(columns=ordered_columns, fill_value='') # Use reindex to ensure all columns are present

        response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
        response['Content-Disposition'] = 'attachment; filename="leads_export.csv"'
        df.to_csv(response, index=False, encoding='utf-8-sig')
        return response
    
    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated, IsAdminOrManagerUser])
    def builder_performance(self, request):
        """
        Aggregates performance metrics for each property (builder project).
        - Total Leads
        - Total Site Visits (based on Lead status)
        - Total Conversions
        - Conversion Rate
        """
        try:
            # This query annotates each Property with the required counts.
            # I am assuming the property name field is 'title'. 
            # Please change 'title' to the correct field name from your Property model.
            performance_data = Property.objects.annotate(
                leads=Count('lead'),
                visits=Count('lead', filter=Q(lead__status__in=['Site Visit Done', 'Site Visit Scheduled'])),
                conversions=Count('lead', filter=Q(lead__status='Converted'))
            ).annotate(
                rate=Case(
                    When(leads__gt=0, then=Cast(F('conversions'), FloatField()) * 100.0 / Cast(F('leads'), FloatField())),
                    default=Value(0.0),
                    output_field=FloatField()
                )
            ).values(
                'title', # <-- IMPORTANT: Change 'title' if your property model uses a different field (e.g., 'name')
                'leads',
                'visits',
                'conversions',
                'rate'
            ).order_by('-conversions') # Order by most conversions

            # Filter out properties that have no leads
            active_projects = [p for p in performance_data if p['leads'] > 0]

            return Response(active_projects)

        except Exception as e:
            import traceback
            print(f"Error in builder_performance endpoint: {str(e)}")
            print(traceback.format_exc())
            return Response(
                {'error': 'An error occurred while fetching builder performance data'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )