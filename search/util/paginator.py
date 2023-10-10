from django.core.paginator import Paginator, Page
from rest_framework.pagination import BasePagination, _positive_int, _get_displayed_page_numbers, _get_page_links
from collections import OrderedDict
from django.core.paginator import InvalidPage
from django.template import loader
from django.utils.encoding import force_str
from django.utils.translation import gettext_lazy as _
from rest_framework.compat import coreapi, coreschema
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.settings import api_settings
from rest_framework.utils.urls import replace_query_param, remove_query_param


class DSLPaginator(Paginator):

    def __init__(self, *args, **kwargs):
        super(DSLPaginator, self).__init__(*args, **kwargs)
        self._count = self.object_list.hits.total

    def page(self, number):
        number = self.validate_number(number)
        return Page(self.object_list, number, self)


class DSLPageNumberPagination(BasePagination):
    """
    http://api.example.org/accounts/?page=4
    http://api.example.org/accounts/?page=4&page_size=100
    """
    page_size = api_settings.PAGE_SIZE
    django_paginator_class = DSLPaginator

    page_query_param = 'page'
    page_query_description = _('A page number within the paginated result set.')

    page_size_query_param = "page_size"
    page_size_query_description = _('Number of results to return per page.')

    max_page_size = None
    template = 'rest_framework/pagination/numbers.html'
    invalid_page_message = _('Invalid page.')
    queryset_count = None
    currency_page = None
    start_index = None
    end_index = None

    def paginate_queryset(self, queryset, request, view=None):
        page_size = self.get_page_size(request)
        if not page_size:
            return None

        self.current_page = int(self.get_page_number(request))
        self.start_index = (self.current_page - 1) * page_size
        self.end_index = self.start_index + page_size
        queryset.extra(track_total_hits=True)
        query = queryset[self.start_index:self.end_index].execute()
        self.queryset_count = queryset.count()
        paginator = self.django_paginator_class(query, page_size)
        try:
            self.page = paginator.page(1)
        except InvalidPage as exc:
            msg = self.invalid_page_message.format(
                page_number=self.current_page, message=str(exc)
            )
            raise NotFound(msg)

        if paginator.num_pages > 1 and self.template is not None:
            # The browsable API should display pagination controls.
            self.display_page_controls = True

        self.request = request
        return list(self.page)

    def get_page_number(self, request):
        return request.query_params.get(self.page_query_param, 1)

    def get_paginated_response(self, data):
        return Response(OrderedDict([
            ('count', self.page.paginator.count if self.queryset_count is None else self.queryset_count),
            ('next', self.get_next_link()),
            ('previous', self.get_previous_link()),
            ('results', data)
        ]))

    def get_paginated_response_schema(self, schema):
        return {
            'type': 'object',
            'properties': {
                'count': {
                    'type': 'integer',
                    'example': 123,
                },
                'next': {
                    'type': 'string',
                    'nullable': True,
                    'format': 'uri',
                    'example': 'http://api.example.org/accounts/?{page_query_param}=4'.format(
                        page_query_param=self.page_query_param)
                },
                'previous': {
                    'type': 'string',
                    'nullable': True,
                    'format': 'uri',
                    'example': 'http://api.example.org/accounts/?{page_query_param}=2'.format(
                        page_query_param=self.page_query_param)
                },
                'results': schema,
            },
        }

    def get_page_size(self, request):
        if self.page_size_query_param:
            try:
                return _positive_int(
                    request.query_params[self.page_size_query_param],
                    strict=True,
                    cutoff=self.max_page_size
                )
            except (KeyError, ValueError):
                pass

        return self.page_size

    def get_next_link(self):
        if self.end_index >= self.queryset_count:
            return None
        url = self.request.build_absolute_uri()
        page_number = self.current_page + 1
        return replace_query_param(url, self.page_query_param, page_number)

    def get_previous_link(self):
        if self.start_index < self.page_size:
            return None
        url = self.request.build_absolute_uri()
        page_number = self.current_page - 1
        if page_number == [1, 0]:
            return remove_query_param(url, self.page_query_param)
        return replace_query_param(url, self.page_query_param, page_number)

    def get_html_context(self):
        base_url = self.request.build_absolute_uri()

        def page_number_to_url(page_number):
            if page_number == 1:
                return remove_query_param(base_url, self.page_query_param)
            else:
                return replace_query_param(base_url, self.page_query_param, page_number)

        current = self.page.number
        final = self.page.paginator.num_pages
        page_numbers = _get_displayed_page_numbers(current, final)
        page_links = _get_page_links(page_numbers, current, page_number_to_url)

        return {
            'previous_url': self.get_previous_link(),
            'next_url': self.get_next_link(),
            'page_links': page_links
        }

    def to_html(self):
        template = loader.get_template(self.template)
        context = self.get_html_context()
        return template.render(context)

    def get_schema_fields(self, view):
        assert coreapi is not None, 'coreapi must be installed to use `get_schema_fields()`'
        assert coreschema is not None, 'coreschema must be installed to use `get_schema_fields()`'
        fields = [
            coreapi.Field(
                name=self.page_query_param,
                required=False,
                location='query',
                schema=coreschema.Integer(
                    title='Page',
                    description=force_str(self.page_query_description)
                )
            )
        ]
        if self.page_size_query_param is not None:
            fields.append(
                coreapi.Field(
                    name=self.page_size_query_param,
                    required=False,
                    location='query',
                    schema=coreschema.Integer(
                        title='Page size',
                        description=force_str(self.page_size_query_description)
                    )
                )
            )
        return fields

    def get_schema_operation_parameters(self, view):
        parameters = [
            {
                'name': self.page_query_param,
                'required': False,
                'in': 'query',
                'description': force_str(self.page_query_description),
                'schema': {
                    'type': 'integer',
                },
            },
        ]
        if self.page_size_query_param is not None:
            parameters.append(
                {
                    'name': self.page_size_query_param,
                    'required': False,
                    'in': 'query',
                    'description': force_str(self.page_size_query_description),
                    'schema': {
                        'type': 'integer',
                    },
                },
            )
        return parameters
