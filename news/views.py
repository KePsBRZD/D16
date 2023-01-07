from django.contrib.auth.models import User
from django.shortcuts import render, reverse, redirect
from datetime import datetime, timedelta
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, TemplateView
from .models import Post, Category, PostCategory, Subscribers, Author, Comment
from .filters import PostFilter
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from .forms import PostForm
from django.urls import reverse_lazy
from django.http import HttpResponseRedirect, HttpResponse
from django.core.mail import send_mail, mail_managers
from django.views import View
from django.contrib.auth.decorators import login_required
from django.db.models.signals import post_save
from .tasks import email_add_post, monday_8am
from django.views.decorators.cache import cache_page
from django.core.cache import cache
# Create your views here.

#@cache_page(60 * 15) # в аргументы к декоратору передаём количество секунд, которые хотим, чтобы страница держалась в кэше. Внимание! Пока страница находится в кэше, изменения, происходящие на ней, учитываться не будут!
#def my_view(request):
#    ...

class PostsList(ListView):

    model = Post
    ordering = "created"
    template_name = "news.html"
    context_object_name = "posts"
    paginate_by = 5

    #def get_queryset(self):
    #    queryset = super().get_queryset()
    #    self.filterset = PostFilter(self.request.GET, queryset=queryset)

    #    return self.filterset.qs


    #def get_context_data(self, **kwargs):
    #    context = super().get_context_data(**kwargs)
    #    context['filterset'] = self.filterset
    #    return context

class PostSearch(ListView):
    model = Post
    ordering = 'created'
    template_name = 'search.html'
    context_object_name = 'posts_search'
    paginate_by = 5

    def get_queryset(self):
        queryset = super().get_queryset()
        self.filterset = PostFilter(self.request.GET, queryset=queryset)

        return self.filterset.qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filterset'] = self.filterset
        return context

class PostDetail(DetailView):

    model = Post
    template_name = "new.html"
    context_object_name = "post"

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)
        context["time_now"] = datetime.utcnow()

        return context

    def get_object(self, *args, **kwargs):
        obj = cache.get(f'news-{self.kwargs["pk"]}', None)
        if not obj:
            obj = super().get_object(queryset=self.queryset)
            cache.set(f'news-{self.kwargs["pk"]}', obj)

        return obj

class PostCreate(PermissionRequiredMixin, CreateView):
    permission_required = ('news.add_post')
    form_class = PostForm
    model = Post
    template_name = 'create.html'
    context_object_name = 'postcreate'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = PostForm()

        return context

    def post(self, request, *args, **kwargs):
        form = self.form_class(request.POST)
        if form.is_valid():
            title = request.POST['title']
            text = request.POST['text']
            email = subscribers_list(request.POST['cats'])
            email_add_post.delay(title, text, email)
            form.save()



class PostUpdate(PermissionRequiredMixin, UpdateView):
    permission_required = ('news.change_post')
    form_class = PostForm
    model = Post
    template_name = 'new_edit.html'
    success_url = '/search/'

    def get_object(self, **kwargs):
        id = self.kwargs.get('pk')
        return Post.objects.get(pk=id)


class PostDelete(PermissionRequiredMixin, DeleteView):
    permission_required = ('news.delete_post')
    model = Post
    template_name = 'new_delete.html'
    success_url = reverse_lazy('post_list')
    success_url = '/search/'


class AddSubscribers(LoginRequiredMixin, TemplateView):
    model = Post
    template_name = 'subscribers.html'

    def get_context_data(self, **kwargs):
        user_id = self.request.user.pk
        category = PostCategory.objects.filter(post_id=self.kwargs.get('pk'))
        for cat in category:
            if not Subscribers.objects.filter(user_id=user_id, cats_id=cat.category_id):
                Subscribers.objects.create(user_id=user_id, cats_id=cat.category_id)


def subscribers_list(categories):
    email_list = []
    for category in categories:
        cats = Subscribers.objects.filter(cats_id=category)
        for user in cats:
            emails = User.objects.filter(id=user.user_id)
            for email in emails:
                email_list.append(email.email)
    return email_list


