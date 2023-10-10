import abc
from django.http import HttpResponse
from elasticsearch_dsl import Q
from django.db.models import Q as QQ
from rest_framework.pagination import PageNumberPagination
from rest_framework.views import APIView
from core.documents import ArticleDocument, UserDocument, CategoryDocument
from core.models import Article
from core.serializers import ArticleSerializer, UserSerializer, CategorySerializer
from search.util.paginator import DSLPageNumberPagination


class PaginatedElasticSearchAPIView(APIView, DSLPageNumberPagination):
    serializer_class = None
    document_class = None

    @abc.abstractmethod
    def generate_q_expression(self, query):
        """This method should be overridden
        and return a Q() expression."""

    def get(self, request, query):
        try:
            q = self.generate_q_expression(query)
            search = self.document_class.search().query(q)
            results = self.paginate_queryset(search, request, view=self)
            serializer = self.serializer_class(results, many=True)
            return self.get_paginated_response(serializer.data)
        except Exception as e:
            return HttpResponse(e, status=500)


class SearchUsers(PaginatedElasticSearchAPIView):
    serializer_class = UserSerializer
    document_class = UserDocument

    def generate_q_expression(self, query):
        return Q('bool',
                 should=[
                     Q('match', username=query),
                     Q('match', first_name=query),
                     Q('match', last_name=query),
                 ], minimum_should_match=1)


class SearchCategories(PaginatedElasticSearchAPIView):
    serializer_class = CategorySerializer
    document_class = CategoryDocument

    def generate_q_expression(self, query):
        return Q(
            'multi_match', query=query,
            fields=[
                'name',
                'description',
            ], fuzziness='auto')


class SearchArticles(PaginatedElasticSearchAPIView):
    serializer_class = ArticleSerializer
    document_class = ArticleDocument

    def generate_q_expression(self, query):
        return Q(
            'multi_match', query=query,
            fields=[
                'title',
                'author',
                'type',
                'content'
            ])


class SearchArticlesDjango(APIView):
    serializer_class = ArticleSerializer

    def get(self, request, query):
        try:
            self.pagination_class = PageNumberPagination()
            search = Article.objects.filter(
                QQ(content__contains=query) or QQ(title__contains=query))
            results = self.pagination_class.paginate_queryset(search, request, view=self)
            serializer = self.serializer_class(results, many=True)
            return self.pagination_class.get_paginated_response(serializer.data)
        except Exception as e:
            return HttpResponse(e, status=500)

# from essential_generators import DocumentGenerator
# from core.models import Category, Article, ARTICLE_TYPES
# from django.contrib.auth.models import User
# import random
# document_generator_instance = DocumentGenerator()
# document_generator_instance.init_sentence_cache(500000)
# all_categories = Category.objects.all()
# all_user = User.objects.all()
# for i in range(100000):
#    article = Article.objects.create(title=document_generator_instance.sentence(),
#                                     author=all_user[random.randint(0, all_user.count() - 1)],
#                                     content=document_generator_instance.paragraph(15, 50),
#                                     type=ARTICLE_TYPES[random.randint(0, len(ARTICLE_TYPES) - 1)][0])
#    article.categories.add(all_categories[random.randint(0, all_categories.count() - 1)])
#    print(f"{i} Adım eklendi.")
