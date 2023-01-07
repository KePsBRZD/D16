from django.urls import path
from .views import PostsList, PostDetail, PostCreate, PostSearch, PostUpdate, PostDelete, AddSubscribers
from django.views.decorators.cache import cache_page

urlpatterns = [
    path("", cache_page(60*1)(PostsList.as_view()), name='post_list'),
    path("<int:pk>", PostDetail.as_view()),
    path('create/', PostCreate.as_view()),
    path('search/', cache_page(60*5)(PostSearch.as_view())),
    path("<int:pk>/update/", PostUpdate.as_view()),
    path("<int:pk>/delete/", PostDelete.as_view()),
    path('subscribers/<int:pk>', AddSubscribers.as_view(), name='add_subscribers'),
]
