"""
Shared admin base classes.

Domain models are soft-deleted, so the admin must show deleted rows rather
than pretending they vanished.
"""
from django.contrib import admin


#: Bookkeeping every domain model carries. Useful to look at, but nobody
#: types these in, so they are tucked into a collapsed section at the bottom
#: rather than shown above the fields the person actually came to fill in.
RECORD_FIELDS = (
    "id", "created_at", "updated_at", "created_by", "updated_by",
    "is_deleted", "deleted_at", "deleted_by",
)


class BaseModelAdmin(admin.ModelAdmin):
    """Sensible defaults for models inheriting core.models.BaseModel."""

    readonly_fields = ("id", "created_at", "updated_at", "created_by", "updated_by")
    list_per_page = 50
    save_on_top = True

    def get_fieldsets(self, request, obj=None):
        """
        Put the real fields first and the bookkeeping last.

        Only applies where the admin class has not laid out its own
        fieldsets — those were written deliberately and are left alone.
        """
        if self.fieldsets:
            return super().get_fieldsets(request, obj)

        every_field = list(self.get_fields(request, obj))
        record = [f for f in every_field if f in RECORD_FIELDS]
        content = [f for f in every_field if f not in RECORD_FIELDS]

        fieldsets = [(None, {"fields": content})]
        if record:
            fieldsets.append(("Record", {"fields": record, "classes": ("collapse",)}))
        return fieldsets

    def get_queryset(self, request):
        # Include soft-deleted rows; an administrator needs to see everything.
        model = self.model
        if hasattr(model, "all_objects"):
            return model.all_objects.get_queryset()
        return super().get_queryset(request)

    def save_model(self, request, obj, form, change):
        if not change and hasattr(obj, "created_by") and obj.created_by is None:
            obj.created_by = request.user
        if hasattr(obj, "updated_by"):
            obj.updated_by = request.user
        super().save_model(request, obj, form, change)
