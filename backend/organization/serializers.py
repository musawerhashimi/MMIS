"""Faculty, department, policy, academic year and deadline serializers."""
from rest_framework import serializers

from organization.models import (
    AcademicYear,
    Department,
    DepartmentPolicy,
    Faculty,
    ResearchArea,
    StageDeadline,
)


class FacultySerializer(serializers.ModelSerializer):
    department_count = serializers.SerializerMethodField()

    class Meta:
        model = Faculty
        fields = ("id", "name", "code", "description", "department_count", "created_at")

    def get_department_count(self, obj) -> int:
        return obj.departments.count()


class DepartmentPolicySerializer(serializers.ModelSerializer):
    """
    The department's own rules.

    Every field here answers a question that turned out to differ between
    departments, so this is the screen a head of department visits once at
    setup and rarely again.
    """

    class Meta:
        model = DepartmentPolicy
        fields = (
            "id",
            "topic_approval_mode",
            "topic_approval_votes_required",
            "supervisor_assignment_mode",
            "default_max_students_per_supervisor",
            "allow_group_monographs",
            "max_students_per_monograph",
            "committee_size",
            "supervisor_grade_weight",
            "committee_grade_weight",
            "passing_grade",
            "use_fixed_stage_deadlines",
            "supervisor_response_days",
            "student_inactivity_days",
            "similarity_threshold",
        )

    def validate(self, attrs):
        # Weights are only meaningful together, so check the combined result
        # whether one or both were sent.
        supervisor = attrs.get(
            "supervisor_grade_weight",
            getattr(self.instance, "supervisor_grade_weight", 40),
        )
        committee = attrs.get(
            "committee_grade_weight",
            getattr(self.instance, "committee_grade_weight", 60),
        )
        if supervisor + committee != 100:
            raise serializers.ValidationError(
                {
                    "supervisor_grade_weight": (
                        f"The two grade weights must add up to 100 "
                        f"(currently {supervisor + committee})."
                    )
                }
            )
        return attrs


class DepartmentSerializer(serializers.ModelSerializer):
    faculty_name = serializers.CharField(source="faculty.name", read_only=True)
    head_name = serializers.CharField(source="head.display_name", read_only=True)
    policy = DepartmentPolicySerializer(read_only=True)
    student_count = serializers.SerializerMethodField()
    supervisor_count = serializers.SerializerMethodField()

    class Meta:
        model = Department
        fields = (
            "id",
            "name",
            "code",
            "description",
            "faculty",
            "faculty_name",
            "head",
            "head_name",
            "policy",
            "student_count",
            "supervisor_count",
            "created_at",
        )

    def get_student_count(self, obj) -> int:
        from core.enums import Role

        return obj.members.filter(role=Role.STUDENT, is_active=True).count()

    def get_supervisor_count(self, obj) -> int:
        from core.enums import Role

        return obj.members.filter(
            role__in=[Role.SUPERVISOR, Role.HEAD_OF_DEPARTMENT], is_active=True
        ).count()

    def create(self, validated_data):
        # A department is unusable without rules, so it gets defaults at once
        # rather than failing the first time someone submits a topic.
        department = super().create(validated_data)
        DepartmentPolicy.objects.get_or_create(department=department)
        return department


class AcademicYearSerializer(serializers.ModelSerializer):
    monograph_count = serializers.SerializerMethodField()

    class Meta:
        model = AcademicYear
        fields = (
            "id",
            "name",
            "start_date",
            "end_date",
            "is_current",
            "is_closed",
            "monograph_count",
        )

    def get_monograph_count(self, obj) -> int:
        return obj.monographs.count()

    def validate(self, attrs):
        start = attrs.get("start_date", getattr(self.instance, "start_date", None))
        end = attrs.get("end_date", getattr(self.instance, "end_date", None))
        if start and end and end <= start:
            raise serializers.ValidationError(
                {"end_date": "The year must end after it starts."}
            )
        return attrs


class ResearchAreaSerializer(serializers.ModelSerializer):
    monograph_count = serializers.SerializerMethodField()

    class Meta:
        model = ResearchArea
        fields = ("id", "name", "description", "department", "monograph_count")

    def get_monograph_count(self, obj) -> int:
        return obj.monographs.count()


class StageDeadlineSerializer(serializers.ModelSerializer):
    stage_label = serializers.SerializerMethodField()

    class Meta:
        model = StageDeadline
        fields = (
            "id",
            "department",
            "academic_year",
            "stage",
            "stage_label",
            "due_date",
            "description",
        )

    def get_stage_label(self, obj) -> str:
        from core.enums import MonographStage

        return dict(MonographStage.choices).get(obj.stage, obj.stage)
