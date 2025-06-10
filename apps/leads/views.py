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
from django.db.models import Count, Sum, Q
from django.db.models.functions import TruncMonth, TruncDate, Coalesce
from decimal import Decimal 
from django.contrib.auth import get_user_model

User = get_user_model()

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
        Calculates and returns the performance metrics for each agent.
        """
        # Filter for users who are agents
        agents = User.objects.filter(role='agent')

        # Annotate the queryset with performance data
        performance_queryset = agents.annotate(
            deals=Count('assigned_leads', filter=Q(assigned_leads__status='Converted')),
            total_leads=Count('assigned_leads'),
            revenue=Coalesce(Sum(
                'assigned_leads__property__price',
                filter=Q(assigned_leads__status='Converted')
            ), Decimal('0.0'))
        ).order_by('-revenue')

        # Format the data for the frontend
        formatted_data = []
        for agent in performance_queryset:
            full_name = agent.get_full_name() or agent.username
            
            # Build the full URL for the profile image
            avatar_url = None
            if agent.profile_image:
                avatar_url = request.build_absolute_uri(agent.profile_image.url)
            
            # Calculate conversion rate
            conversion_rate = 0
            if agent.total_leads > 0:
                conversion_rate = round((agent.deals / agent.total_leads) * 100)

            formatted_data.append({
                "agent": full_name,
                "deals": agent.deals,
                "revenue": agent.revenue,
                "avatar": avatar_url,
                "conversionRate": conversion_rate,
            })

        return Response(formatted_data)
    
    @action(detail=False, methods=['get'])
    def revenue_overview(self, request):
        """
        Calculates total revenue and sales from converted leads, grouped by month.
        'Sales' is simulated as 60% of revenue for demonstration.
        """
        converted_leads = Lead.objects.filter(
            status='Converted',
            property__price__isnull=False
        )
        revenue_by_month = converted_leads.annotate(
            month=TruncMonth('updated_at')
        ).values('month').annotate(
            total_revenue=Sum('property__price')
        ).values('month', 'total_revenue').order_by('month')

        formatted_data = []
        for item in revenue_by_month:
            # Safely get revenue, defaulting to 0 if it's None
            revenue = item.get('total_revenue') or Decimal('0.0')
            formatted_data.append({
                "name": item['month'].strftime('%b'),
                "revenue": revenue,
                # --- THIS LINE IS CORRECTED ---
                "sales": revenue * Decimal('0.6') # Convert 0.6 to a Decimal
            })
        return Response(formatted_data)
        
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