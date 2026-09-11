# 공시렌즈 · 기업공시 변경점과 근거 추적

React·TypeScript 정적 웹서비스와 Python 일괄 분석 파이프라인입니다. 삼성전자·SK하이닉스·LG전자의 2024·2025 사업보고서 비교를 지원하도록 구현했습니다.

**현재는 기능 베타입니다. 실제 공시 6개는 아직 수집·검수하지 않았습니다.** 기본 화면의 실제 데이터 목록은 비어 있고, `?demo=1`에서만 가상 예시를 볼 수 있습니다. 기업명은 대상 선택 UI를 보여주기 위한 것이며 예시 수치·서술은 실제 기업 현황이 아닙니다.

## 실행

Node.js 24와 Python 3.12 이상을 사용합니다.

```powershell
npm ci
python -m pip install -r requirements.txt
npm run dev
```

공개 API 서버나 데이터베이스는 필요하지 않습니다. 예시 주소는 `/?demo=1`, 특정 근거 공유는 `?demo=1#company=samsung&pair=samsung-2024-2025-demo&change=change-1` 형태입니다.

## 구현 기능

- 기업 선택, 연결 매출·영업이익 비교, 내용 변경·추가·삭제 필터, 표현 변경 접기
- 양쪽 원문 문단·표·문맥, 선택한 표 행 강조, 모바일 이전·이후 탭, 근거 공유 URL
- 원 단위 정수 보존, 흑자·적자 전환과 0 기준값 처리, 재작성·기준 차이 증감률 보류
- 접수번호·SHA-256으로 원본 보관, 동일·이동 문단 제외, 분할·병합 대응 후보
- 선택적 LLM 분석, 인용문·분석 범위 검증, 월 비용 사전 예약
- 비공개 검수 자료, 검수자 확인, 검수 이후 변경 감지, 공개 필드 허용목록
- 버전 파일 보존 및 공개 목록 포인터의 원자적 갱신

## 실제 공시 연결

`.env.example`을 프로젝트 루트의 `.env`로 복사하고 로컬 편집기로 입력합니다. `.env`, `private/`, 원본 ZIP, 검수 메모, 인증키는 Git에서 제외됩니다. 키를 코드나 `VITE_` 변수에 넣지 마세요.

```dotenv
DART_API_KEY=발급받은_인증키
LLM_API_KEY=사용할_서비스의_인증키
LLM_BASE_URL=https://사용할-서비스의-공식-주소/v1
LLM_MODEL=사용할_모델
LLM_INPUT_KRW_PER_MILLION=1000
LLM_OUTPUT_KRW_PER_MILLION=5000
LLM_MONTHLY_BUDGET_KRW=30000
```

위 단가는 설정 형식 예시이며 실제 요금이 아닙니다. 공급자의 현재 단가·환율·부가 비용을 반영한 보수적인 원화 단가로 바꿉니다. LLM 서비스는 HTTPS Chat Completions, JSON object 출력, max_tokens를 지원해야 합니다. 숨은 추론 과금 등으로 출력 제한이 과금 상한을 보장하지 않는 공급자는 사용하지 마세요. 공급자 측 비용 한도도 함께 설정합니다.

LLM 키 없이도 수집·추출·수작업 검수와 웹서비스는 사용할 수 있습니다. 자동 설명 생성을 생략하고 draft.json에 근거가 있는 변경점을 직접 작성할 수 있습니다.

```powershell
python -m pipeline.cli collect
python -m pipeline.cli prepare --company samsung
python -m pipeline.cli analyze --company samsung
```

`private/work/samsung/review.html`에서 대상 문단과 표를 확인합니다. 다른 기업 식별자는 skhynix, lge입니다. 수집은 최종보고서(last_reprt_at=Y), 사업보고서 A001, 2024·2025 사업연도, 연결 주요계정 11011을 사용합니다. 본문 XML을 유일하게 식별하지 못하면 중단합니다. 실제 원본 레이아웃 검증은 키 연결 이후 필요합니다.

### 재무 근거 연결

`private/work/<기업>/bindings.template.json`을 같은 폴더의 `bindings.json`으로 복사합니다.

- blockId: 검수 자료의 연결손익계산서 표 식별자
- row, column: 표의 본문 행·당기 열. 0부터 시작하고 헤더 행 제외
- priorColumn: 이후 보고서의 전기 비교 열
- multiplier: 원=1, 천 원=1000, 백만 원=1000000, 억 원=100000000
- period: 해당 연도 1월 1일~12월 31일인지 원문에서 확인
- apiMismatchReviewed: API 접수번호·값이 표와 다를 때만 원문 검수 후 true
- compatible: 연결 범위·통화·기간 등 비교 기준이 동일한지 확인

```powershell
python -m pipeline.cli assemble --company samsung
```

이전 당기와 이후 전기 값이 다르면 증감률을 보류합니다. 표에 단위가 없거나 계정이 모호하면 자동 확정하지 않습니다. 지원하지 않는 XML 구조가 발견되면 파서를 수정하고 회귀 테스트를 추가한 뒤 다시 준비합니다.

### 서술 검수와 공개

draft.json의 before·after 인용과 ID, 분석 범위 내 문단 이동·분할·병합, 사업 사실에 대한 과도한 추정을 확인합니다. 검수한 변경점만 `reviewStatus: "approved"`로 바꿉니다. 불확실한 대응은 `kind: "uncertain", reviewStatus: "needs_review"`로 남길 수 있으며 공개 시 설명은 고정 안내문으로 바뀝니다.

```powershell
python -m pipeline.cli review --company samsung --reviewer "실제 검수자 이름" --acknowledge
python -m pipeline.cli publish --company samsung
python -m pipeline.cli validate-public
```

**review는 사람이 원문을 확인한 뒤 실행하는 확인 절차입니다. 자동 테스트로 인간 검수를 대신하지 않습니다.** 승인에 초안과 재무 근거 매핑 해시를 기록하며 수정 후에는 재검수가 필요합니다. 공개 시 원본을 재파싱하고 금액을 재계산합니다. `public/data/<기업>/<버전>.json`에 결과를 저장하고 기존 파일은 유지합니다.

## 검증과 출시 기준

```powershell
python -m unittest discover -s tests -v
python -m pipeline.cli validate-public
npm test
npx playwright install chromium
npm run test:browser
npm run build
```

브라우저 테스트는 데스크톱과 모바일에서 실제 목록 빈 상태, 예시 전환, 필터, 손익 전환, 공유 주소 복원, 근거 탭, 오류 화면과 가로 넘침을 확인합니다.

실제 서술 평가셋은 준비된 것으로 간주하지 않습니다. 세 기업의 문단 묶음 60개를 사람이 작성하고 20개 dev·40개 test로 나눕니다. 항목 형식은 `{id, companyId, split, before: [문단ID], after: [문단ID], kind}`입니다. 예측 파일은 같은 id·before·after·kind를 사용합니다.

```powershell
python -m pipeline.cli evaluate --truth private/evaluation/truth.json --predictions private/evaluation/predictions.json
```

실데이터 출시에 필요한 기준: 재무값 12개 전수 대조, 근거 링크 전수 확인, 문단 대응 정확도 90%·실질 변화 재현율 85%, 실제 사용자 5명 중 4명의 2분 내 과제 성공, 지정 모바일 환경에서 3초 이내 주요 내용 표시. **가상 자동 테스트는 실제 서술 평가·사용성 검증 결과가 아닙니다.**

## 운영

주 1회 운영자가 실행합니다. 자동 예약 작업은 생성하지 않습니다.

```powershell
python -m pipeline.cli check-updates
```

정정이 발견되면 수집→준비→분석→검수→공개를 다시 진행합니다. 오류·쿼터 초과 시 공개본은 유지됩니다. 비용은 입력 바이트 기반의 보수적인 토큰 상한과 최대 출력으로 선예약하며 네트워크 실패 시에도 예약을 되돌리지 않습니다. `private/budget.json`에 기록하고 `private/budget.lock`으로 중복 예약을 막습니다. 비정상 종료 후 잠금은 분석이 실행 중이 아님을 확인한 운영자가 제거합니다.

## GitHub Pages

현재 로그인에는 workflow 권한이 없어, 검증한 정적 파일을 gh-pages 브랜치에 올립니다. Settings → Pages → Deploy from a branch → gh-pages / 루트로 설정합니다. 변경사항을 커밋한 뒤 npm run deploy를 실행하면 Python·화면 테스트, 공개 데이터 검증, 빌드를 모두 통과한 dist만 업로드합니다. main 푸시만으로 자동 배포되지는 않습니다.

자동 작업 권한을 추가하면 docs/github-pages-workflow.yml을 .github/workflows/pages.yml로 옮기고 Pages Source를 GitHub Actions로 바꿀 수 있습니다. 상대 경로와 해시 URL이므로 저장소 하위 경로에서도 동작합니다. 인증키는 로컬에만 보관합니다.

## 현재 한계

- 인증키 미설정으로 실제 6개 원문 수집·파싱과 LLM 제공자 연결은 검증 전입니다.
- 재무표의 열·단위·기간 및 서술 내용에 인간 검수가 필요합니다.
- 문자열 유사도 후보 검색은 강한 표현 변화를 누락할 수 있습니다. 실제 평가셋과 전체 후보 검수가 필요합니다.
- WebMCP는 지원 브라우저에서 비교 읽기·근거 이동 도구를 등록합니다. 지원 브라우저에서의 통합 검증은 별도입니다.

## 데이터 출처

- [OpenDART 공시검색](https://opendart.fss.or.kr/guide/detail.do?apiGrpCd=DS001&apiId=2019001)
- [공시서류 원본](https://opendart.fss.or.kr/guide/detail.do?apiGrpCd=DS001&apiId=2019003)
- [단일회사 주요계정](https://opendart.fss.or.kr/guide/detail.do?apiGrpCd=DS003&apiId=2019016)

예시 텍스트는 직접 작성한 가상 내용이며 DART에서 추출한 인용문이 아닙니다.

### 실데이터 공개 게이트

publish 명령은 `private/release-checks.json`이 없으면 중단합니다. 가상 예시 사이트의 배포에는 이 파일이 필요하지 않습니다. 실제 평가 후 다음 형식으로 기록하세요. 값은 예시가 아니라 실제 검증 결과로 채워야 합니다.

```json
{
  "reviewedBy": "실제 검증자",
  "checkedAt": "실제 확인일",
  "draftHashes": {"samsung": "해당 draft.json의 pipeline.core.digest 결과", "skhynix": "동일 형식", "lge": "동일 형식"},
  "financialValuesChecked": 12,
  "allEvidenceLinksChecked": true,
  "evaluation": {"truth": "private/evaluation/truth.json", "predictions": "private/evaluation/predictions.json", "model": "평가한 모델명"},
  "usability": [{"participant": "익명 식별자", "success": true, "seconds": 90}],
  "performance": {"device": "측정 기기", "network": "측정 네트워크", "renderMs": 2000}
}
```

usability에는 서로 다른 참가자 5명의 실제 결과가 필요합니다. 위 숫자는 형식 예시이며 달성한 기록이 아닙니다. 초안 해시는 `python -c "from pipeline.core import load,digest; print(digest(load('private/work/samsung/draft.json')))"`으로 확인합니다. 초안 수정 시 재검수하고 출시 검증 해시를 다시 기록해야 합니다.
