from rest_framework.routers import DefaultRouter

from reviews.views import DiscussionViewSet, ReviewCommentViewSet, ReviewViewSet

app_name = "reviews"

router = DefaultRouter()
router.register("comments", ReviewCommentViewSet, basename="review-comment")
router.register("discussions", DiscussionViewSet, basename="discussion")
router.register("", ReviewViewSet, basename="review")

urlpatterns = router.urls
