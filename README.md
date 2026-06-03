# NTE RT Installer

Neverness To Everness / NTE 레이트레이싱 옵션 표시를 돕기 위한 한국어 로컬 설치기입니다.

이 도구는 OptiScaler를 게임 폴더에 배치하고, NTE용 GPU spoof 설정을 `OptiScaler.ini`에 적용합니다. 자동 다운로드 서버나 웹 UI 없이, 사용자가 직접 받은 OptiScaler 공식 Release 폴더만 사용합니다.

## 매우 중요: 실험용 / 사용자 책임

이 프로젝트는 실험용 도구입니다. 안전을 보장하지 않습니다.

게임 실행 폴더에 외부 프록시 DLL을 배치하는 방식이므로, 게임 보안 시스템 차단, 게임 크래시, 런처 파일 검증 실패, 계정 제재 가능성이 있습니다. 이 도구를 실행하고 사용하는 책임은 전적으로 사용자 본인에게 있습니다.

보안 경고가 뜨면 즉시 사용을 중단하고 원복하세요.

## 기능

- 기본 NTE 설치 경로 자동 입력: `C:\Program Files\Neverness To Everness`
- `HTGame.exe`가 있는 Win64 폴더 탐색
- `winmm.dll`, `dxgi.dll` 프록시 선택
- 설치 전 `_nte_rt_kr_backups` 백업 생성
- 최근 백업 원복
- RTX 5090 / RTX 4090 / RTX 5080M spoof 프로필
- 기본 설정은 `Registry=false`, `User32=false`

## 포함하지 않는 것

이 저장소는 OptiScaler 바이너리를 포함하지 않습니다.

OptiScaler는 공식 GitHub Release에서 직접 받아 주세요:

https://github.com/optiscaler/OptiScaler/releases/latest

다운로드한 `.7z`를 풀고, 그 폴더를 설치기에서 `OptiScaler 압축 해제 폴더`로 선택하면 됩니다. 폴더 안에는 `OptiScaler.dll`과 `OptiScaler.ini`가 있어야 합니다.

## 사용법

1. Python 3을 설치합니다.
   - https://www.python.org/downloads/windows/
   - 설치 중 `Add python.exe to PATH`를 체크하는 것을 권장합니다.
2. OptiScaler 공식 Release를 다운로드하고 `.7z` 압축을 풉니다.
   - https://github.com/optiscaler/OptiScaler/releases/latest
   - 압축 해제 폴더 안에 `OptiScaler.dll`과 `OptiScaler.ini`가 있어야 합니다.
3. NTE와 런처를 완전히 종료합니다.
4. `run_as_admin.bat`을 실행합니다.
5. Windows 권한 확인창을 허용합니다.
6. `Win64 찾기`를 누릅니다.
7. OptiScaler 압축 해제 폴더를 선택합니다.
8. 프록시는 `winmm.dll`을 권장합니다.
9. `상태 확인`을 누릅니다.
10. `백업 후 설치`를 누릅니다.
11. 게임을 켜고 그래픽 프리셋을 극치/Ultra 이상으로 설정합니다.

`py` 또는 `python`을 찾을 수 없다는 메시지가 나오면 Python 3이 설치되어 있지 않거나 PATH에 잡혀 있지 않은 것입니다. Python을 설치한 뒤 다시 실행하세요.

## 문제 해결

OptiScaler 오버레이가 보이면 로드는 성공한 것입니다.

레이트레이싱 옵션이 보이지 않으면 `OptiScaler.ini`의 spoof 설정이 올바른 섹션에 들어갔는지 확인해야 합니다. 이 설치기는 OptiScaler 원본 ini의 기존 키를 직접 교체하도록 작성되어 있습니다.

게임이 켜지지 않으면 `run_as_admin.bat`으로 다시 실행한 뒤 `최근 백업으로 원복`을 누르세요.

`winmm.dll`은 권장 프록시입니다. `dxgi.dll`은 대안으로 남겨두지만, 그래픽 후킹에서 흔히 쓰이는 이름이라 게임 보안 시스템에 차단될 가능성이 더 큽니다.

게임 보안 시스템이 `dxgi.dll` 또는 `winmm.dll`을 충돌 프로그램으로 감지하면 해당 DLL을 제거하고 원복하세요. 차단된 환경에서는 사용을 중단하는 것을 권장합니다.

## 주의

이 도구는 게임 실행 폴더에 로컬 프록시 DLL을 배치합니다. 게임 업데이트, 런처 검증, 안티치트 정책, 계정 제재 가능성은 배제할 수 없습니다. 사용자는 본인 책임으로 사용해야 합니다.

## Credits

- OptiScaler: https://github.com/optiscaler/OptiScaler
- Original reference workflow: https://github.com/llg1634/nte-ray-tracing-panel
