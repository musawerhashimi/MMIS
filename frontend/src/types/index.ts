/** Shapes the API returns. Mirrors the serializers in the Django backend. */

export type Role = 'student' | 'supervisor' | 'hod' | 'committee' | 'admin'

export type MonographStage =
  | 'draft'
  | 'topic_submitted'
  | 'topic_approved'
  | 'proposal_submitted'
  | 'under_review'
  | 'revision_required'
  | 'proposal_approved'
  | 'research_in_progress'
  | 'final_submission'
  | 'final_review'
  | 'defense_scheduled'
  | 'defended'
  | 'completed'
  | 'rejected'
  | 'withdrawn'

export type ReviewDecision = 'approved' | 'revision_requested' | 'rejected'
export type DefenseResult = 'passed' | 'passed_with_revisions' | 'failed'
export type DocumentType =
  | 'topic_form'
  | 'proposal'
  | 'chapter'
  | 'final_monograph'
  | 'presentation'
  | 'supporting'
  | 'signed_form'

export interface UserBrief {
  id: string
  username: string
  full_name: string
  display_name: string
  role: Role
  avatar: string | null
}

export interface Permissions {
  is_student: boolean
  is_supervisor: boolean
  is_head_of_department: boolean
  is_committee_member: boolean
  is_admin: boolean
  can_supervise: boolean
}

export interface User extends UserBrief {
  title: string
  email: string
  phone: string
  department: string | null
  department_name: string | null
  is_active: boolean
  last_seen_at: string | null
  created_at: string
  student_profile: StudentProfile | null
  supervisor_profile: SupervisorProfile | null
  permissions: Permissions
}

export interface StudentProfile {
  student_id: string
  enrollment_year: number | null
  program: string
}

export interface SupervisorProfile {
  specialization: string
  max_students: number | null
  is_accepting_students: boolean
  effective_max_students: number
  active_student_count: number
  has_capacity: boolean
}

export interface SupervisorOption {
  id: string
  full_name: string
  display_name: string
  department: string | null
  specialization: string
  active_students: number
  max_students: number | null
  has_capacity: boolean
}

/** An action the current user may take on a monograph right now. */
export interface AvailableAction {
  target: MonographStage
  label: string
  requires_note: boolean
}

export interface MonographListItem {
  id: string
  title: string
  stage: MonographStage
  stage_label: string
  progress_percent: number
  days_in_current_stage: number
  stage_changed_at: string
  supervisor: string | null
  supervisor_name: string | null
  department: string
  department_name: string
  research_area_name: string | null
  student_names: string[]
  academic_year: string
  academic_year_name: string
  final_grade: string | null
  is_finished: boolean
  created_at: string
}

export interface Monograph extends Omit<MonographListItem, 'supervisor'> {
  abstract: string
  keywords: string[]
  objectives: string
  methodology: string
  expected_outcome: string
  closure_reason: string
  completed_at: string | null
  supervisor: UserBrief | null
  supervisor_assigned_at: string | null
  members: MonographMember[]
  available_actions: AvailableAction[]
  can_edit: boolean
  document_count: number
  review_count: number
}

export interface MonographMember {
  id: string
  student: UserBrief
  is_lead: boolean
  contribution: string
}

export interface StageTransition {
  id: string
  from_stage: string
  from_stage_label: string
  to_stage: string
  to_stage_label: string
  actor: UserBrief | null
  note: string
  days_in_previous_stage: number | null
  created_at: string
}

export interface ActivityEntry {
  id: string
  action: string
  description: string
  actor: UserBrief | null
  metadata: Record<string, unknown>
  created_at: string
}

/** The merged timeline returns both kinds, tagged. */
export type TimelineEntry =
  | (StageTransition & { type: 'transition' })
  | (ActivityEntry & { type: 'activity' })

export interface DocumentVersion {
  id: string
  version_number: number
  original_filename: string
  file_size: number
  size_display: string
  extension: string
  content_type: string
  change_note: string
  uploaded_by: UserBrief | null
  download_count: number
  download_url: string
  created_at: string
}

export interface MonographDocument {
  id: string
  monograph: string
  document_type: DocumentType
  document_type_label: string
  title: string
  chapter_number: number | null
  description: string
  is_approved: boolean
  approved_at: string | null
  approved_by: UserBrief | null
  current_version: DocumentVersion | null
  version_count: number
  created_at: string
  versions?: DocumentVersion[]
}

export interface ReviewItem {
  id: string
  page_number: number | null
  section: string
  body: string
  is_resolved: boolean
  resolved_at: string | null
}

export interface Review {
  id: string
  monograph: string
  reviewer: UserBrief
  decision: ReviewDecision
  decision_label: string
  summary: string
  comments: string
  round_number: number
  score: string | null
  document_version: string | null
  document_title: string | null
  document_version_number: number | null
  items: ReviewItem[]
  created_at: string
}

export interface CommitteeMember {
  id: string
  member: UserBrief
  role: string
  role_label: string
  score: string | null
  comments: string
  scored_at: string | null
  has_read_monograph: boolean
  attended: boolean
}

export interface Defense {
  id: string
  monograph: string
  monograph_title: string
  student_names: string[]
  scheduled_at: string | null
  duration_minutes: number
  location: string
  result: DefenseResult | ''
  result_label: string
  held_at: string | null
  supervisor_score: string | null
  committee_average: string | null
  final_grade: string | null
  all_scores_in: boolean
  is_upcoming: boolean
  notes: string
  required_revisions: string
  revisions_due_date: string | null
  committee: CommitteeMember[]
}

export interface Notification {
  id: string
  kind: string
  kind_label: string
  title: string
  body: string
  link: string
  monograph: string | null
  monograph_title: string | null
  actor: UserBrief | null
  is_read: boolean
  read_at: string | null
  metadata: Record<string, unknown>
  created_at: string
}

export interface StageCount {
  stage: MonographStage
  label: string
  count: number
  percent: number
  progress: number
  is_finished: boolean
}

export interface SupervisorLoad {
  id: string
  name: string
  active: number
  completed: number
  capacity: number | null
  utilisation: number | null
  over_capacity: boolean
  awaiting_response: number
}

export interface Bottleneck {
  stage: string
  label: string
  average_days: number
  sample_size: number
}

export interface HodDashboard {
  role: 'head_of_department'
  totals: {
    total: number
    active: number
    completed: number
    rejected: number
    withdrawn: number
    unassigned: number
  }
  attention: {
    awaiting_supervisor: number
    gone_quiet: number
    behind_deadline: number
  }
  by_stage: StageCount[]
  supervisor_load: SupervisorLoad[]
  bottlenecks: Bottleneck[]
  recent_activity: {
    monograph_id: string
    title: string
    to_stage: string
    to_stage_label: string
    actor: string | null
    at: string
  }[]
}

export interface SupervisorDashboard {
  role: 'supervisor'
  totals: { active: number; completed: number; awaiting_me: number }
  awaiting_me: {
    id: string
    title: string
    students: string[]
    stage: MonographStage
    stage_label: string
    waiting_days: number
  }[]
  gone_quiet: {
    id: string
    title: string
    students: string[]
    stage_label: string
    silent_days: number
  }[]
  by_stage: StageCount[]
}

export interface StudentDashboard {
  role: 'student'
  monograph: {
    id: string
    title: string
    stage: MonographStage
    stage_label: string
    progress_percent: number
    days_in_current_stage: number
    supervisor: string | null
  } | null
  latest_feedback: {
    decision: ReviewDecision
    summary: string
    comments: string
    reviewer: string
    at: string
  } | null
  next_deadline: {
    stage: string
    due_date: string
    days_remaining: number
    description: string
  } | null
  defense: {
    scheduled_at: string | null
    location: string
    result: string
    final_grade: string | null
  } | null
  documents: number
  unread_notifications: number
}

export interface CommitteeDashboard {
  role: 'committee'
  assigned_defenses: Defense[]
}

export type Dashboard =
  | HodDashboard
  | SupervisorDashboard
  | StudentDashboard
  | CommitteeDashboard

export interface Paginated<T> {
  count: number
  page: number
  pages: number
  page_size: number
  next: string | null
  previous: string | null
  results: T[]
}

/** Every API failure arrives in this shape. */
export interface ApiError {
  error: {
    code: string
    message: string
    details: Record<string, string | string[]>
  }
}
