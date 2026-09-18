# 공시렌즈 디자인 — Carbon v11 참고

Carbon v11의 밝은 Gray 10 테마, UI Shell, 데이터 표, 버튼, 탭과 간격 체계를 참고한 사용자 지정 구현이다. Carbon React 패키지를 도입하거나 Figma 파일을 그대로 가져온 구현은 아니다. Figma 링크가 로딩되지 않아 아래 공식 문서를 근거로 적용했다.

## 표현 원칙

- 전체 배경 #f4f4f4와 흰색 레이어. 본문 #161616, 보조 문자 #525252, 도움말 #6f6f6f.
- 사용자 요청에 따라 밝고 단순한 색 구성을 유지한다. Carbon 기본 파랑 대신 청록 #007d79를 상호작용 강조색으로 사용한다.
- 48px 상단 바, 화면 가장자리에 붙은 왼쪽 탐색 영역, 모바일 5개 메뉴. 둥근 떠 있는 사이드바와 큰 색상 제목 카드를 제거한다.
- 여백은 8·16·24·32px, 입력 높이 40px, 데이터 행 48px. 제목은 28–36px, 표·버튼은 14px 중심이다.
- 버튼·입력·카드·표는 직각 모서리로 정돈한다. 상태 태그만 둥근 형태를 사용한다.
- 선택한 메뉴는 선과 배경으로, 필터는 밑줄로 구분한다. 상태 문구와 숫자를 유지하고 색에만 의미를 맡기지 않는다.
- 숫자 타일은 레이블과 값의 계층을 분리하고, 검토 항목 목록은 가로 구분선으로 연결한다.
- 재무표는 회색 헤더, 일정한 행 높이, 가로 경계선과 오른쪽 정렬 숫자를 사용한다.
- 실제 PDF의 픽셀·배경·확대 기능은 유지한다. 이전 셀은 회색 점선, 이후 셀은 청록 실선으로 표시한다.
- 키보드 포커스는 2px 외곽선으로 표시하고 reduced-motion을 준수한다. 외부 폰트와 새 런타임 의존성은 추가하지 않는다.
- 역할별 CSS 변수로 색과 간격을 관리한다. 공통 테마는 src/theme.css에서 각 화면 스타일 다음에 적용한다.

## 참고 문서

- [사용자 제공 Carbon v11 Figma](https://www.figma.com/ko-kr/community/file/1157761560874207208/v11-carbon-design-system)
- [테마·색상·레이어](https://carbondesignsystem.com/elements/color/overview/)
- [간격](https://carbondesignsystem.com/elements/spacing/overview/)
- [버튼](https://carbondesignsystem.com/components/button/style/)
- [탭](https://carbondesignsystem.com/components/tabs/style/)
- [데이터 표](https://carbondesignsystem.com/components/data-table/style/)
- [탐색 패널](https://carbondesignsystem.com/components/UI-shell-left-panel/usage/)

데이터, 검수 상태, API 키 처리, 분석 범위는 이 UI 변경의 대상이 아니다.
