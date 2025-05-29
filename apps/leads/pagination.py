from rest_framework.pagination import PageNumberPagination

class StandardResultsSetPagination(PageNumberPagination):
    """
    Custom pagination class to configure how results are paginated.
    Default page size is 10, client can override with 'page_size' query param.
    """
    page_size = 10  # Default number of items per page
    page_size_query_param = 'page_size'  # Allows client to set page_size via query param
    max_page_size = 100  # Maximum page size client can request 
