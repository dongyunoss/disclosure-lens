from .core import load

def evaluate(truth_path,prediction_path):
    truth=load(truth_path);pred=load(prediction_path)
    if len(truth)!=60 or len({x['id'] for x in truth})!=60:raise ValueError('고유한 평가 문단 묶음 60개가 필요합니다.')
    if sum(x['split']=='dev' for x in truth)!=20 or sum(x['split']=='test' for x in truth)!=40:raise ValueError('개발 20개·평가 40개로 분리하세요.')
    if {x['companyId'] for x in truth}!={'samsung','skhynix','lge'}:raise ValueError('세 기업 모두 평가셋에 포함하세요.')
    predictions={x['id']:x for x in pred};samples=[x for x in truth if x['split']=='test']
    correct=found=total=0
    for item in samples:
        p=predictions.get(item['id'],{})
        if set(p.get('before',[]))==set(item['before']) and set(p.get('after',[]))==set(item['after']) and p:correct+=1
        substantive=item['kind'] in {'content','added','removed'}
        if substantive:total+=1;found+=p.get('kind') in {'content','added','removed'}
    accuracy=correct/40;recall=found/total if total else 0
    return dict(testCases=40,alignmentAccuracy=accuracy,substantiveRecall=recall,passed=accuracy>=.9 and recall>=.85)
