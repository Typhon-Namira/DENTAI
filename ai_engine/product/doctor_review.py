"""Immutable doctor feedback and verified-label transitions."""
from copy import deepcopy
from .models import DoctorReview,LabelState,ReviewAction
from .patient_matching import new_id
ALLOWED={LabelState.UNLABELED:{LabelState.AI_PRELABELED},LabelState.AI_PRELABELED:{LabelState.NEEDS_REVIEW,LabelState.VERIFIED},LabelState.NEEDS_REVIEW:{LabelState.HUMAN_CORRECTED,LabelState.VERIFIED},LabelState.HUMAN_CORRECTED:{LabelState.VERIFIED},LabelState.VERIFIED:{LabelState.TRAIN_READY},LabelState.TRAIN_READY:set()}
def create_review(clinic_id,analysis_id,doctor_id,original_ai_output,action,tooth_fdi=None,finding_type=None,corrected_value=None,notes=None):
 return DoctorReview(review_id=new_id('REV'),clinic_id=clinic_id,analysis_id=analysis_id,tooth_fdi=tooth_fdi,finding_type=finding_type,doctor_id=doctor_id,original_ai_output=deepcopy(original_ai_output),doctor_action=ReviewAction(action),corrected_value=corrected_value,notes=notes)
def transition_label(current,target,policy_satisfied=False):
 current,target=LabelState(current),LabelState(target)
 if target not in ALLOWED[current]:raise ValueError(f'invalid label transition {current}->{target}')
 if target==LabelState.TRAIN_READY and not policy_satisfied:raise ValueError('verification policy not satisfied')
 return target
