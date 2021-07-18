from typing import Union
from django.db.models.query import QuerySet
from django.contrib import admin
from django.core.handlers.wsgi import WSGIRequest
from .models import PublicAttachment, PrivateAttachment, Image, GenericAttachment


# https://docs.djangoproject.com/en/2.2/ref/contrib/admin/actions/#writing-action-functions
def delete_everywhere(model_admin: Union[PublicAttachment, PrivateAttachment],
                      request: WSGIRequest,
                      queryset: QuerySet):
    """
    Delete object both in Django and in MinIO too.
    :param model_admin: unused
    :param request: unused
    :param queryset: A QuerySet containing the set of objects selected by the user
    :return:
    """
    del model_admin, request  # We don't need these
    for obj in queryset:
        obj.delete()


delete_everywhere.short_description = "Delete selected objects in Django and MinIO"


@admin.register(Image)
class ImageAdmin(admin.ModelAdmin):
    list_display = ('id', 'image',)
    readonly_fields = ('id', )
    model = Image
    actions = [delete_everywhere, ]


@admin.register(GenericAttachment)
class GenericAttachmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'file',)
    readonly_fields = ('id', )
    model = GenericAttachment
    actions = [delete_everywhere, ]


# Register your models here.
@admin.register(PublicAttachment)
class PublicAttachmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'content_type',)
    readonly_fields = ('id', 'content_object', 'file_name', 'file_size', )
    model = PublicAttachment
    actions = [delete_everywhere, ]

    fieldsets = [

        ('General Information',
         {'fields': ('id',)}),
        ('S3 Object',
         {'fields': ('file_name', 'file_size', 'file',)}),
        ('S3 Object Details',
         {'fields': ('content_object', 'content_type', 'object_id',)}),
    ]

    def get_actions(self, request):
        actions = super().get_actions(request)
        if 'delete_selected' in actions:
            del actions['delete_selected']
        return actions


@admin.register(PrivateAttachment)
class PrivateAttachmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'content_type',)
    readonly_fields = ('id', 'content_object', 'file_name', 'file_size')
    model = PrivateAttachment
    actions = [delete_everywhere, ]

    fieldsets = [

        ('General Information',
         {'fields': ('id',)}),
        ('S3 Object',
         {'fields': ('file_name', 'file_size', 'file',)}),
        ('S3 Object Details',
         {'fields': ('content_object', 'content_type', 'object_id',)}),
    ]

    def get_actions(self, request):
        actions = super().get_actions(request)
        if 'delete_selected' in actions:
            del actions['delete_selected']
        return actions
