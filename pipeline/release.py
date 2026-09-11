"""Release evidence is recorded by the operator; fixtures cannot establish real-world quality."""
from .core import digest, load
from .evaluate import evaluate

def release_gate(root, data):
    checks=load(root/'private'/'release-checks.json')
    if not checks.get('reviewedBy') or not checks.get('checkedAt'):
        raise ValueError('실제 출시 검증자와 확인일이 필요합니다.')
    if checks.get('draftHashes',{}).get(data['companyId'])!=digest(data):
        raise ValueError('현재 초안에 대한 출시 검증 기록이 없습니다.')
    def private_path(value):
        path=(root/value).resolve()
        if not path.is_relative_to((root/'private').resolve()):
            raise ValueError('평가 자료는 private/ 안에 보관하세요.')
        return path
    truth=private_path(checks['evaluation']['truth'])
    predictions=private_path(checks['evaluation']['predictions'])
    result=evaluate(truth,predictions)
    if not result['passed']:raise ValueError('실제 서술 평가가 출시 기준을 통과하지 못했습니다.')
    if checks['evaluation'].get('model')!=data['analysis']['model']:
        raise ValueError('평가한 분석 모델과 공개 대상 모델이 다릅니다.')
    participants=checks['usability']
    if len(participants)!=5 or len({p['participant'] for p in participants})!=5:
        raise ValueError('서로 다른 사용자 5명의 과제 결과가 필요합니다.')
    success=sum(p.get('success') is True and isinstance(p.get('seconds'),(int,float)) and 0<p['seconds']<=120 for p in participants)
    if success<4:raise ValueError('사용성 기준을 통과하지 못했습니다.')
    performance=checks['performance']
    if not performance.get('device') or not performance.get('network') or not isinstance(performance.get('renderMs'),(int,float)) or not 0<performance['renderMs']<=3000:
        raise ValueError('지정 모바일 환경의 3초 이내 표시 검증이 필요합니다.')
    if checks.get('financialValuesChecked')!=12 or checks.get('allEvidenceLinksChecked') is not True:
        raise ValueError('재무값 12개와 모든 근거 링크 확인이 필요합니다.')
    return result
