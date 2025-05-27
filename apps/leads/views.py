from rest_framework import viewsets, permissions, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from .models import Lead
from .serializers import LeadSerializer
from .permissions import IsOwnerOrAssignedOrAdmin, IsAdminOrManagerUser 
# Ensure you have this or a similar permission for import/export

# Assuming pagination.py is in the same directory (your leads app)
from .pagination import StandardResultsSetPagination 

from rest_framework.parsers import MultiPartParser
import pandas as pd
from io import StringIO 
from django.http import HttpResponse
from django.db.models import Count


class LeadViewSet(viewsets.ModelViewSet):
    serializer_class = LeadSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrAssignedOrAdmin]
    
    # Apply the pagination class here
    pagination_class = StandardResultsSetPagination 
    
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    # Ensure your filterset_fields, search_fields, and ordering_fields are correctly defined
    # based on your Lead model and LeadFilter (if you have a custom filterset class)
    filterset_fields = ['status', 'source', 'priority', 'assigned_to', 'created_by'] 
    search_fields = ['name', 'email', 'phone', 'company', 'interest']
    ordering_fields = ['created_at', 'updated_at', 'name', 'status', 'priority']
    ordering = ['-created_at'] # Default ordering

    def get_queryset(self):
        user = self.request.user
        
        if user.is_superuser or getattr(user, 'role', None) == 'admin':
            return Lead.objects.all().select_related('assigned_to', 'created_by')
        elif getattr(user, 'role', None) == 'manager':
            # Managers might see all leads or leads within their team/department
            # Adjust this logic based on your exact requirements for managers
            return Lead.objects.all().select_related('assigned_to', 'created_by')
        else: # Agents or other roles
            # Agents typically see only leads assigned to them
            return Lead.objects.filter(assigned_to=user).select_related('assigned_to', 'created_by')
        # Using select_related to optimize fetching related user details if frequently accessed

    def get_permissions(self):
        """
        Instantiates and returns the list of permissions that this view requires.
        Overrides default permissions for specific actions.
        """
        if self.action in ['import_leads', 'export_leads']:
            # Only Admin or Manager can import/export
            # Ensure IsAdminOrManagerUser is correctly defined in your permissions.py
            return [permissions.IsAuthenticated(), IsAdminOrManagerUser()] 
        return [permission() for permission in self.permission_classes]

    @action(detail=False, methods=['get'])
    def dashboard_stats(self, request):
        # This action typically wouldn't be paginated by default DRF pagination.
        # If you need to paginate these stats (unlikely), you'd handle it manually.
        queryset = self.filter_queryset(self.get_queryset()) # Apply filters if any
        
        status_stats = queryset.values('status').annotate(
            count=Count('status')
        ).order_by('status')
        
        source_stats = queryset.values('source').annotate(
            count=Count('source')
        ).order_by('source')
        
        priority_stats = queryset.values('priority').annotate(
            count=Count('priority')
        ).order_by('priority')
        
        recent_leads_qs = queryset.order_by('-created_at')[:5]
        # Use the serializer for consistent data structure, especially for related fields
        recent_leads_data = LeadSerializer(recent_leads_qs, many=True, context={'request': request}).data
        
        total_leads = queryset.count()
        converted_leads = queryset.filter(status='Converted').count()
        new_leads = queryset.filter(status='New').count()
        qualified_leads = queryset.filter(status='Qualified').count()
        
        conversion_rate = (converted_leads / total_leads * 100) if total_leads > 0 else 0
        
        return Response({
            'total_leads': total_leads,
            'converted_leads': converted_leads,
            'new_leads': new_leads,
            'qualified_leads': qualified_leads,
            'conversion_rate': round(conversion_rate, 1),
            'status_distribution': list(status_stats),
            'source_distribution': list(source_stats),
            'priority_distribution': list(priority_stats),
            'recent_leads': recent_leads_data,
        })


    @action(detail=False, methods=['post'], parser_classes=[MultiPartParser])
    def import_leads(self, request):
        # Permission check (IsAdminOrManagerUser) is handled by get_permissions()
        if 'file' not in request.FILES:
            return Response({'error': 'No file provided'}, status=status.HTTP_400_BAD_REQUEST)
        
        file = request.FILES['file']

        if not file.name.lower().endswith(('.csv', '.xlsx', '.xls')):
            return Response(
                {'error': 'Unsupported file format. Please use CSV, XLSX, or XLS.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
            
        try:
            if file.name.lower().endswith('.csv'):
                try:
                    df = pd.read_csv(file, dtype=str, keep_default_na=False) # Read all as string initially
                except UnicodeDecodeError:
                    file.seek(0) 
                    df = pd.read_csv(file, encoding='latin1', dtype=str, keep_default_na=False)
            elif file.name.lower().endswith(('.xlsx', '.xls')):
                df = pd.read_excel(file, dtype=str, keep_default_na=False) # Read all as string initially
            else: 
                return Response(
                    {'error': 'Internal error: Unsupported file format processing.'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )

            df.columns = [col.strip().lower() for col in df.columns]
            
            created_count = 0
            skipped_rows_details = [] 

            for index, row in df.iterrows():
                # Prepare data, ensuring empty strings for missing optional fields
                lead_data = {
                    'name': row.get('name', ''),
                    'email': row.get('email', ''),
                    'phone': row.get('phone', ''),
                    'status': row.get('status', 'New'),
                    'source': row.get('source', 'Website'),
                    'interest': row.get('interest', ''),
                    'priority': row.get('priority', 'Medium'),
                    'company': row.get('company', ''),
                    'position': row.get('position', ''),
                    'budget': row.get('budget', ''),
                    'timeline': row.get('timeline', ''),
                    'requirements': row.get('requirements', ''),
                    'notes': row.get('notes', ''),
                    'tags': [tag.strip() for tag in str(row.get('tags', '')).split(',') if tag.strip()] if str(row.get('tags', '')).strip() else [],
                    # assigned_to will be set to the importing user by default
                }
                
                # Pass request to serializer context for created_by and potentially assigned_to logic
                serializer = LeadSerializer(data=lead_data, context={'request': request})
                if serializer.is_valid():
                    # serializer.save() will use created_by from context
                    # and if assigned_to is not in lead_data, it might be null or set by serializer logic
                    serializer.save(assigned_to=request.user) # Explicitly assign to current user
                    created_count += 1
                else:
                    skipped_rows_details.append({'row_number': index + 2, 'errors': serializer.errors})
            
            message = f'{created_count} leads imported successfully.'
            response_status = status.HTTP_201_CREATED

            if skipped_rows_details:
                message += f' {len(skipped_rows_details)} rows were skipped due to errors.'
                # For a production app, you might log these errors or provide a way for the user to download them
                # For now, just adjusting the status if no leads were created but some were skipped.
                if created_count == 0:
                    response_status = status.HTTP_400_BAD_REQUEST # Or 200 OK with error details

            return Response(
                {'message': message, 'created_count': created_count, 'skipped_count': len(skipped_rows_details), 'skipped_details': skipped_rows_details if skipped_rows_details else None},
                status=response_status
            )
            
        except pd.errors.EmptyDataError:
            return Response({'error': 'The uploaded file is empty or not a valid CSV/Excel file.'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            print(f"Error during lead import: {str(e)}") 
            return Response(
                {'error': 'An unexpected error occurred during import. Please check file format and content.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def export(self, request):
        # Permission check (IsAdminOrManagerUser) is handled by get_permissions()
        # For export, we usually want all filtered data, not just one page.
        # So, we bypass the viewset's default pagination for this action.
        queryset = self.filter_queryset(self.get_queryset()) # Apply filters
        
        # Manually serialize all data from the filtered queryset
        serializer = LeadSerializer(queryset, many=True, context={'request': request})
        
        # Convert to DataFrame
        # We can simplify this if the serializer output is already flat enough
        # or handle nested data (like assigned_to_detail) more explicitly
        
        # A more robust way to handle nested serializer data for export:
        data_to_export = []
        for lead_data in serializer.data:
            flat_lead = lead_data.copy() # Start with a copy
            if 'assigned_to_detail' in flat_lead and flat_lead['assigned_to_detail']:
                flat_lead['assigned_to_name'] = f"{flat_lead['assigned_to_detail'].get('first_name','')} {flat_lead['assigned_to_detail'].get('last_name','')}".strip()
                flat_lead['assigned_to_email'] = flat_lead['assigned_to_detail'].get('email','')
            else:
                flat_lead['assigned_to_name'] = 'Unassigned'
                flat_lead['assigned_to_email'] = ''
            del flat_lead['assigned_to_detail'] # remove nested object
            
            if 'created_by_detail' in flat_lead and flat_lead['created_by_detail']:
                 flat_lead['created_by_name'] = f"{flat_lead['created_by_detail'].get('first_name','')} {flat_lead['created_by_detail'].get('last_name','')}".strip()
            else:
                flat_lead['created_by_name'] = ''
            del flat_lead['created_by_detail']

            if isinstance(flat_lead.get('tags'), list): # Ensure tags are comma-separated string
                flat_lead['tags'] = ','.join(flat_lead['tags'])

            data_to_export.append(flat_lead)

        df = pd.DataFrame(data_to_export)
        
        # Define specific columns and their order for export if needed
        # export_columns = ['id', 'name', 'email', 'phone', 'company', 'status', 'source', 'priority', 'assigned_to_name', 'created_at', ...]
        # df = df[export_columns]


        response = HttpResponse(content_type='text/csv; charset=utf-8-sig') # Added charset
        response['Content-Disposition'] = 'attachment; filename="leads_export.csv"'
        
        df.to_csv(response, index=False, encoding='utf-8-sig') # utf-8-sig for better Excel compatibility
        return response

