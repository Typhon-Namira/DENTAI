"""Immutable exam comparison using structurally compatible findings."""
SEVERITY={'HEALTHY':0,'FILLING':1,'CROWN':1,'ROOT_CANAL_TREATMENT':2,'CARIES':2,'APICAL_PERIODONTITIS':3,'ROOT_FRAGMENT':3,'DEEP_CARIES':4}
def index(exam):return {str(x['fdi']):x for x in exam.get('teeth',exam.get('tooth_results',[]))}
def findings(t):return set(t.get('final_findings',[x['type']for x in t.get('findings',[])]))
def compare_patient_exams(previous_exam,current_exam):
 a,b=index(previous_exam),index(current_exam);new=[];resolved=[];persistent=[];changed=[];rest=[];missing=[];states={}
 for fdi in sorted(set(a)|set(b),key=int):
  if fdi not in a:missing.append({'fdi':fdi,'change':'NEWLY_DETECTED_TOOTH'});states[fdi]='UNKNOWN';continue
  if fdi not in b:missing.append({'fdi':fdi,'change':'NO_LONGER_DETECTED'});states[fdi]='UNKNOWN';continue
  old,newset=findings(a[fdi]),findings(b[fdi]);n=newset-old;r=old-newset;p=old&newset
  new +=[{'fdi':fdi,'finding':x}for x in n];resolved +=[{'fdi':fdi,'finding':x}for x in r];persistent +=[{'fdi':fdi,'finding':x}for x in p]
  if n or r:
   comparable=all(x in SEVERITY for x in old|newset)
   state=('CHANGE_UNCERTAIN'if not comparable else'PROGRESSED'if max(map(lambda x:SEVERITY[x],newset),default=0)>max(map(lambda x:SEVERITY[x],old),default=0)else'IMPROVED'if r else'NEW_FINDING');changed.append({'fdi':fdi,'before':sorted(old),'after':sorted(newset),'state':state});states[fdi]=state
  else:states[fdi]='STABLE_WITH_CONFIDENCE_CHANGE'if a[fdi].get('finding_confidences')!=b[fdi].get('finding_confidences')else'STABLE'
  oldr={x for x in old if x in('FILLING','CROWN','ROOT_CANAL_TREATMENT','IMPLANT')};newr={x for x in newset if x in('FILLING','CROWN','ROOT_CANAL_TREATMENT','IMPLANT')}
  if oldr!=newr:rest.append({'fdi':fdi,'before':sorted(oldr),'after':sorted(newr)})
 warnings=dental_identity_consistency(previous_exam,current_exam)
 return {'available':True,'new_findings':new,'resolved_findings':resolved,'persistent_findings':persistent,'changed_findings':changed,'restoration_changes':rest,'missing_tooth_changes':missing,'tooth_states':states,'identity_consistency_warnings':warnings}
def dental_identity_consistency(previous,current):
 a,b=index(previous),index(current);stable={'IMPLANT','CROWN','ROOT_CANAL_TREATMENT'};lost=[]
 for fdi,t in a.items():
  old=findings(t)&stable;new=findings(b[fdi])if fdi in b else set()
  if old-new:lost.append({'code':'IDENTITY_CONSISTENCY_WARNING','fdi':fdi,'message':f"Previous stable dental pattern at FDI {fdi} is absent; verify patient identity."})
 return lost
