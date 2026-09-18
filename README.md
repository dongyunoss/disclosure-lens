# 공시렌즈 · 투자 검토 포인트와 공시 근거 추적

첫 화면은 **재무제표에서 투자자가 더 확인할 항목을 찾는 투자 검토 화면**입니다. 삼성전자 실제 2025 사업보고서의 비교열에서 20개 재무 항목을 추출해 수익성·운전자본·현금 창출·재무 여력·자본 배분의 10가지 기준을 적용합니다. 각 결과에 판단 기준, 다음 검토 질문, 실제 PDF 표의 이전·이후 금액 셀을 연결합니다. FCF·지역별 매출 분해는 세부 분석으로 유지합니다.

결과는 확인 우선 / 주요 변화 / 설정 기준 미해당 / 판단 보류로 구분합니다. 고정 임계값을 사용하는 탐색 도구이며 업종 보정이나 투자 성과 검증은 수행하지 않았습니다. 기업의 좋고 나쁨, 원인의 확정, 매수·매도를 판정하지 않습니다. 주석·사업부·동종업계·밸류에이션 등 미분석 영역도 화면에 명시합니다.

현재 투자 검토 결과는 삼성전자 1개 보고서로 제한됩니다. 다른 기업은 준비 중입니다. 자동 감지는 인증키와 상시 실행 환경 연결 전이며, 기존 감지 파이프라인의 자동 공개 대상은 FCF·매출 산술 분석입니다. 새 검토 화면은 원문 셀까지 검증한 정적 데이터만 제공합니다.

React·TypeScript 정적 웹서비스와 Python 일괄 분석 파이프라인입니다. 삼성전자·SK하이닉스·LG전자의 2024·2025 사업보고서 비교를 지원하도록 구현했습니다.

**현재는 기능 베타입니다. 삼성전자·LG전자의 2024·2025 사업보고서 4개에서 실제 발췌문을 제공합니다.** 기업 공식 IR PDF의 짧은 사업 설명과 연결 매출·영업이익 표 행, 총 12개 항목을 원문 페이지와 함께 확인할 수 있습니다. 자동 비교 결과는 아직 수집·검수가 끝나지 않아 비어 있고, `?demo=1`에서만 가상 예시를 볼 수 있습니다. 기업명은 대상 선택 UI를 보여주기 위한 것이며 예시 수치·서술은 실제 기업 현황이 아닙니다.

## 실행

Node.js 24와 Python 3.12 이상을 사용합니다.

```powershell
npm ci
python -m pip install -r requirements.txt
npm run dev
```

공개 API 서버나 데이터베이스는 필요하지 않습니다. 예시 주소는 `/?demo=1`, 특정 근거 공유는 `?demo=1#company=samsung&pair=samsung-2024-2025-demo&change=change-1` 형태입니다.

## 투자 검토 데이터 재생성

보관된 실제 PDF가 필요합니다. 금액을 손으로 입력하지 않고 정확한 원문 행과 3개 비교열을 찾아 추출합니다. 연결 기준·연간 기간·단위·파일 해시를 확인하고, 금액이 속한 PDF 셀을 유일하게 찾지 못하면 생성을 중단합니다.

명령: python -m pip install -r requirements-pdf.txt → python -m pipeline.review_sources

공개 전 검증: python -m pipeline.cli validate-public. 모든 판단을 다시 계산하고, 원문 셀의 백만원 값을 원 단위로 환산해 일치 여부와 이미지 SHA-256을 검사합니다. 원본은 private에 보관하고 실제 표의 필요한 부분만 공개합니다. 기존 두 보고서 서술 비교의 전수 검수·출시 게이트는 유지합니다.

공유 예: /?view=review&company=samsung&review=samsung-2025-review-v1&finding=receivables&fact=receivables
기존 비교: /?view=compare 또는 /?demo=1

세부 기준은 [투자 검토 방법론](docs/investment-review.md)을 참고하세요.

## 구현 기능

- **수치 변화 원인 화면** (`?view=drivers`): 실제 삼성전자 2025 보고서의 FCF·지역별 매출 기여도, 원문 표 연결
- **실제 공시표 위 강조 표시**: 분석 항목을 선택하면 원본 PDF 표 이미지의 이전·이후 금액 셀을 강조합니다. 확대·강조 켜기/끄기·모바일 셀 이동·선택 항목 공유 URL을 지원합니다.
- 신규·정정 정기보고서와 잠정실적 감지 작업, 5분 대기 주기, 중복 방지·재시도·상태 표시 (인증키와 상시 실행 환경 연결 전)
- 기업 선택, 연결 매출·영업이익 비교, 내용 변경·추가·삭제 필터, 표현 변경 접기
- 양쪽 원문 문단·표·문맥, 선택한 표 행 강조, 모바일 이전·이후 탭, 근거 공유 URL
- 원 단위 정수 보존, 흑자·적자 전환과 0 기준값 처리, 재작성·기준 차이 증감률 보류
- 접수번호·SHA-256으로 원본 보관, 동일·이동 문단 제외, 분할·병합 대응 후보
- 선택적 LLM 분석, 인용문·분석 범위 검증, 월 비용 사전 예약
- 비공개 검수 자료, 검수자 확인, 검수 이후 변경 감지, 공개 필드 허용목록
- 버전 파일 보존 및 공개 목록 포인터의 원자적 갱신

## API 키 없이 실제 원문 발췌

`?view=excerpts`에서 실제 보고서를 선택합니다. 검색, 문장 일부 선택, 출처 포함 복사, PDF 해당 페이지 열기를 지원합니다. 예: `?view=excerpts&source=samsung-2025&excerpt=revenue`. 복사에는 회사·회계연도·단위·표 열·PDF 페이지와 원문 주소가 포함됩니다. 클립보드 접근이 제한되면 직접 복사할 텍스트를 제공합니다.

```powershell
python -m pipeline.excerpts
python -m pipeline.excerpts --refresh
```

첫 명령은 없는 PDF를 수집하고, `--refresh`는 공식 URL에서 다시 받습니다. `config/excerpts.json`에 공식 URL과 검증할 페이지·문구를 관리합니다. 원본은 `private/official-pdf/`에 보관하고, 공개용 짧은 인용문·재무표 행·SHA-256·출처는 `public/excerpts/library.json`으로 생성합니다. 원본 회사·연도·연간 기간·연결 기준·단위·선택 행을 검증하지 못하면 공개 파일을 바꾸지 않습니다.

현재는 삼성전자·LG전자 각 2개 보고서만 제공합니다. SK하이닉스 공식 PDF 연결은 준비 중입니다. 기업 IR 게시본이며 **최종 정정 여부는 미확인**입니다. PDF 물리 페이지와 본문에 인쇄된 페이지가 달라 두 번호를 구분합니다. 원문 발췌 제공은 자동 변경점 분석에 대한 인간 검수나 출시 기준 통과를 뜻하지 않습니다.

## OpenDART 수집·비교 분석 연결

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

브라우저 테스트는 데스크톱과 모바일에서 실제 목록 빈 상태, 예시 전환, 필터, 손익 전환, 공유 주소 복원, 근거 탭, 오류 화면과 가로 넘침을 확인합니다. 원문 발췌의 실제 출처, 페이지 이동, 검색, 부분 복사, 복사 실패 대체 화면, 예시와 실제 원문 사이 전환도 검증합니다.

실제 서술 평가셋은 준비된 것으로 간주하지 않습니다. 세 기업의 문단 묶음 60개를 사람이 작성하고 20개 dev·40개 test로 나눕니다. 항목 형식은 `{id, companyId, split, before: [문단ID], after: [문단ID], kind}`입니다. 예측 파일은 같은 id·before·after·kind를 사용합니다.

```powershell
python -m pipeline.cli evaluate --truth private/evaluation/truth.json --predictions private/evaluation/predictions.json
```

실데이터 출시에 필요한 기준: 재무값 12개 전수 대조, 근거 링크 전수 확인, 문단 대응 정확도 90%·실질 변화 재현율 85%, 실제 사용자 5명 중 4명의 2분 내 과제 성공, 지정 모바일 환경에서 3초 이내 주요 내용 표시. **가상 자동 테스트는 실제 서술 평가·사용성 검증 결과가 아닙니다.**

## 운영

기존 고정 연도 비교는 주 1회 운영자가 확인할 수 있습니다. 아래 신규 공시 감지 작업은 별도이며, 이 저장소만 배포해도 자동으로 실행되는 것은 아닙니다.

```powershell
python -m pipeline.cli check-updates
```

정정이 발견되면 수집→준비→분석→검수→공개를 다시 진행합니다. 오류·쿼터 초과 시 공개본은 유지됩니다. 비용은 입력 바이트 기반의 보수적인 토큰 상한과 최대 출력으로 선예약하며 네트워크 실패 시에도 예약을 되돌리지 않습니다. `private/budget.json`에 기록하고 `private/budget.lock`으로 중복 예약을 막습니다. 비정상 종료 후 잠금은 분석이 실행 중이 아님을 확인한 운영자가 제거합니다.

## 신규 공시 감지와 수치 원인 분석

**현재 공개 화면은 실제 보관 PDF로 계산한 삼성전자 분석입니다. 실시간 감지 작업은 실행되지 않았습니다.** OpenDART 인증키가 없고 상시 실행 호스트가 아직 연결되지 않았습니다. GitHub Pages는 화면만 제공하므로 감지 작업은 켜져 있는 PC나 서버에서 따로 실행해야 합니다. 호스팅 비용은 기존 월 예산 안에서 별도 확정해야 합니다.

```powershell
# 보관된 실제 삼성전자 PDF에서 다시 생성
python -m pipeline.driver_sources
# 신규 공시를 한 번 감지하고 비공개 자동 분석 저장
python -m pipeline.monitor
# 상시 실행: 자동 산술 결과를 미검수로 명시해 공개하고 기존 Pages에 배포
python -m pipeline.monitor --watch --publish-automatic --deploy
```

원본 표 이미지 재생성에는 `python -m pip install -r requirements-pdf.txt`가 먼저 필요합니다. 이미 저장된 수치 분석에 표 강조만 연결하려면 `python -m pipeline.table_overlays`를 실행합니다. 이 기능은 실제 PDF를 표 영역으로 발췌해 표시하며, 표를 다시 그리거나 숫자를 바꾸지 않습니다. 강조는 별도 화면 레이어입니다. 원본 PDF 해시·금액 문자열·PDF 셀 위치를 검증하고, 좌표는 이미지 크기에 대한 비율로 저장해 확대해도 같은 셀을 가리킵니다. 공개 배포 검사에서 표 이미지 해시도 확인합니다. 현재 위치 매핑은 삼성전자 2025 사업보고서 PDF 89쪽 현금흐름표와 185쪽 지역별 매출표에 제공됩니다. 다른 보고서는 원문 위치 매핑이 추가되어야 강조를 제공합니다.

감지 대상은 기존 3개 기업의 사업·반기·1/3분기 보고서, 정정본, 잠정실적 및 매출액/손익구조 공시입니다. 매 실행이 끝난 뒤 300초 대기합니다. 공시검색 노출, 재무 API 갱신, 실행·배포 시간은 별도이므로 즉시 완료나 5분 이내 완료를 보장하지 않습니다. 초회에는 최근 7일, 이후 마지막 성공 확인일에서 2일을 겹쳐 검색합니다. 접수번호별 작업을 보존하고 조회 실패 시 확인 위치를 전진시키지 않습니다. 분석 실패는 간격을 늘려 재시도하며 12회 후 운영자 검수로 전환합니다. 한 번에 최대 5개를 처리합니다. 잠정실적만으로 FCF를 만들지 않습니다.

`private/monitor/state.json`에 처리 이력, `private/live/<접수번호>/`에 ZIP·재무 응답·분석·설명 후보를 보관합니다. `--publish-automatic`을 명시한 경우에만 자동 분석을 `public/drivers/`에 공개합니다. 숫자 설명에는 항상 **자동 산출·미검수**를 표시합니다. 기존의 전수 검수 사업보고서 비교 공개 조건은 바꾸지 않았습니다. 배포 작업은 main 브랜치의 지정 저장소에서만 작동하며 다른 코드 변경이 있으면 중단합니다. 전체 검증을 통과한 정적 파일만 배포합니다. 화면은 1분마다 공개 상태를 다시 읽고 마지막 확인이 15분보다 오래되면 작동 중이라는 표시를 내립니다.

### 어떤 이유를 설명하는가

- FCF는 영업활동현금흐름에서 유형·무형자산 취득 **현금지출**을 뺀 값입니다. 자산 장부금액 증가나 전체 투자현금흐름을 CAPEX로 대신하지 않습니다. 각 구성요소 변화의 FCF 기여도를 정수로 계산하고 합계를 검증합니다. 회사가 발표한 다른 FCF 정의와 구분합니다.
- 정기보고서는 같은 보고서의 전년 동기 비교값으로 비교합니다. 분·반기 매출은 누적 열을 사용해 현금흐름 기간과 맞춥니다. 단기 열을 누적 열로 대체하지 않습니다. API 접수번호·연결 기준·통화·연도·보고서 종류가 맞지 않거나 CAPEX 계정이 누락/중복이면 관련 계산을 보류합니다.
- 지역별 매출 변화는 전체 매출 변화에 대한 **산술 기여**입니다. 수출 증가, 가격·물량·환율 변화의 인과 설명과 다릅니다. 자동 XML 지역표 처리는 연결·지역·매출 절, 명시된 연도 열, 단위, 총계가 모두 확인되는 연간 표만 허용합니다. 다른 구조와 분·반기는 수작업 매핑 검수 전까지 보류합니다. 지금 공개된 삼성전자 지역표는 PDF 열과 원문을 별도로 확인한 매핑을 사용합니다.
- LLM 연결 시 관련 문단에서 회사 설명과 추정을 구분한 `claims.draft.json`을 생성합니다. 모델·프롬프트 버전과 사용한 범위를 기록하고 인용문 원문 일치를 검사합니다. **회사 설명 후보와 추정은 비공개 검수 대상으로 남고 자동 공개하지 않습니다.** 원문 근거 없는 “유럽향 수출 증가 때문”을 생성해 확정 원인처럼 표시하지 않습니다.

실제 API와의 통합 검증, 24시간 운영, 기업별 지역·제품 표 매핑 확대, 서술 원인 검수·공개 흐름은 후속 연결이 필요합니다. 자동 숫자 분석의 단위·누락·정정 예외와 화면 흐름은 테스트로 검증하지만, 이는 신규 공시의 전수 인간 검수를 뜻하지 않습니다.

## GitHub Pages

현재 로그인에는 workflow 권한이 없어, 검증한 정적 파일을 gh-pages 브랜치에 올립니다. Settings → Pages → Deploy from a branch → gh-pages / 루트로 설정합니다. 변경사항을 커밋한 뒤 npm run deploy를 실행하면 Python·화면 테스트, 공개 데이터 검증, 빌드를 모두 통과한 dist만 업로드합니다. main 푸시만으로 자동 배포되지는 않습니다.

자동 작업 권한을 추가하면 docs/github-pages-workflow.yml을 .github/workflows/pages.yml로 옮기고 Pages Source를 GitHub Actions로 바꿀 수 있습니다. 상대 경로와 해시 URL이므로 저장소 하위 경로에서도 동작합니다. 인증키는 로컬에만 보관합니다.

## 현재 한계

- 실제 IR PDF 4개 발췌는 제공 중입니다. 인증키 미설정으로 OpenDART XML 수집·파싱과 LLM 제공자 연결, 6개 보고서의 최종 정정 확인은 검증 전입니다.
- 재무표의 열·단위·기간 및 서술 내용에 인간 검수가 필요합니다.
- 문자열 유사도 후보 검색은 강한 표현 변화를 누락할 수 있습니다. 실제 평가셋과 전체 후보 검수가 필요합니다.
- WebMCP는 지원 브라우저에서 비교 읽기·근거 이동 도구를 등록합니다. 지원 브라우저에서의 통합 검증은 별도입니다.

## 데이터 출처

- [삼성전자 공식 사업보고서 목록](https://www.samsung.com/sec/ir/reports-disclosures/business-report/)
- [LG전자 공식 사업보고서 목록](https://www.lge.co.kr/company/investor/businessReport)
- [OpenDART 공시검색](https://opendart.fss.or.kr/guide/detail.do?apiGrpCd=DS001&apiId=2019001)
- [공시서류 원본](https://opendart.fss.or.kr/guide/detail.do?apiGrpCd=DS001&apiId=2019003)
- [단일회사 주요계정](https://opendart.fss.or.kr/guide/detail.do?apiGrpCd=DS003&apiId=2019016)
- [단일회사 전체 재무제표](https://opendart.fss.or.kr/guide/detail.do?apiGrpCd=DS003&apiId=2019020)

예시 텍스트는 직접 작성한 가상 내용이며 DART에서 추출한 인용문이 아닙니다.

### 실데이터 공개 게이트

publish 명령은 `private/release-checks.json`이 없으면 중단합니다. 가상 예시와 출처가 명시된 원문 발췌 화면의 배포에는 이 파일이 필요하지 않습니다. 자동 비교 공개에는 계속 필요합니다. 실제 평가 후 다음 형식으로 기록하세요. 값은 예시가 아니라 실제 검증 결과로 채워야 합니다.

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
