# 🚀 ComfyUI Anima LLM Prompt Rewriter

**Anima LLM Prompt Rewriter**는 단보루(Danbooru) 스타일의 나열식 캐릭터/배경 태그를 로컬 LLM을 사용하여 자연스러운 영문 소설 형태의 프롬프트로 자동 변환해 주는 **ComfyUI 전용 커스텀 노드**입니다. 

다인물 생성 시 발생하는 **속성 번짐(Concept Bleeding) 현상을 원천 차단**하며, 시스템 VRAM 상태와 서버 구동 여부를 스스로 판단하는 **스마트 하이브리드 엔진**을 탑재하여 OOM(Out of Memory) 에러 없이 최적의 속도를 보장합니다.

---

## 📑 목차
1. [✨ 주요 기능 (Features)](#-주요-기능-features)
2. [📦 설치 및 선행 조건 (Installation & Prerequisites)](#-설치-및-선행-조건-installation--prerequisites)
   - [공통 필수 조건](#1-공통-필수-조건-모든-사용자)
   - [[A] 간편 설치 모드 (Standalone)](#a-간편-설치-모드-standalone---일반-유저용)
   - [[B] 고성능 하이엔드 모드 (API Server)](#b-고성능-하이엔드-모드-llama-server-api---고급-유저용)
3. [💻 사용 방법 (How to Use)](#-사용-방법-how-to-use)
4. [🎛️ 입출력 규격 (Inputs & Outputs)](#️-입출력-규격-inputs--outputs)
5. [❓ 자주 묻는 질문 (Troubleshooting)](#-자주-묻는-질문-troubleshooting)

---

## ✨ 주요 기능 (Features)

### 1. 다인물 속성 번짐 방지 (Natural Language Rewriting)
단보루 스타일의 나열식 태그를 입력받아, 로컬 LLM을 통해 영문 소설 형태의 자연어 프롬프트로 완벽하게 재구성합니다. 인물 1, 인물 2, 배경, 행동 태그를 각각 분리하여 LLM에 전달하며, 주어와 동사가 명확한 문장으로 번역되어 2인 이상의 캐릭터 생성 시 서로의 특징(머리색, 옷 등)이 섞이는 **'속성 번짐(Concept Bleeding)' 현상을 원천 차단**합니다.

### 2. 자동 감지 하이브리드 엔진 (Hybrid Execution & VRAM Safe)
사용자의 PC 환경에 맞춰 두 가지 모드를 스스로 판단하고 전환합니다.
* **API 통신 모드 (서버 감지 시):** 노드 실행 시 `127.0.0.1:8080`으로 헬스체크(Ping)를 보냅니다. 백그라운드에 `llama-server`가 켜져 있는 것이 감지되면, 무거운 모델을 VRAM으로 불러오지 않고 즉시 API를 쏴서 텍스트 결과만 받아옵니다. VRAM 충돌(OOM)을 100% 방지하는 최고의 속도 모드입니다.
* **Standalone 로컬 로드 모드 (서버 없을 시):** 서버가 꺼져 있다면, 선택한 GGUF 모델을 ComfyUI 프로세스 내의 VRAM으로 직접 불러옵니다.
* 🧹 **스마트 가비지 컬렉션:** Standalone 모드에서 텍스트 번역이 끝나는 즉시 `del llm`과 `torch.cuda.empty_cache()`를 실행하여 **VRAM을 강제로 즉시 반환**합니다. 이어지는 무거운 이미지 생성 모델(SDXL/Anima 등)에게 VRAM 자리를 온전히 양보합니다.

### 3. 완벽한 안전장치 (Fail-Safe & Fallback)
어떤 돌발 상황에서도 이미지 생성 워크플로우가 멈추지 않습니다.
* **스위치 OFF 시:** 사용자가 노드에서 LLM 기능을 끄면(`enable_llm=False`), 노드는 즉시 작동을 멈추고 사용자가 직접 입력한 '한국어 수동 상세 묘사'와 '단보루 원본 태그'를 그대로 다음 노드로 패스스루(Pass-through) 합니다.
* **에러 발생 시 자동 우회:** LLM 모듈 미설치, 모델 파일 손상, 빈 문자열 반환 등 예기치 못한 에러 발생 시 시스템을 멈추지 않습니다. 내부적으로 에러를 흡수하고 **즉시 원본 태그 우회 모드(Fallback)로 전환**하여 생성을 계속 진행합니다.

### 4. 동적 폴더 탐색 및 스마트 UI (Dynamic Model Discovery)
* **자동 폴더 생성:** ComfyUI 디렉토리에 `models/LLM` 폴더가 없다면 최초 실행 시 알아서 생성합니다.
* **깔끔한 UI 표기:** 하위 폴더에 있는 모든 `.gguf` 파일을 자동으로 탐색하여 노드의 드롭다운 메뉴에 보여줍니다. 복잡한 절대 경로 대신 `LLM/gemma.gguf` 처럼 직관적이고 깔끔한 이름만 UI에 노출시킵니다.

### 5. 지능형 출력 라우팅 (Smart Output Routing)
노드 우측의 4개 출력 핀은 상황에 따라 밸브를 자동으로 조절합니다.
* **LLM 번역 성공 시:** 1번 핀(자연어)으로 완성된 문장만 내보내고, 나머지 핀(원본 태그)은 강제로 공백(`""`) 처리하여 뒤쪽 파이프라인에서 프롬프트가 중복 폭발하는 것을 막습니다.
* **LLM 번역 실패/OFF 시:** 1번 핀으로 수동 입력값을, 나머지 핀으로 각각의 원본 태그들을 살려 보내어 기존의 태그 결합 방식대로 정상 작동하도록 길을 열어줍니다.

---

## 📦 설치 및 선행 조건 (Installation & Prerequisites)

본 노드는 환경에 따라 **[A] 간편 설치(Standalone) 모드**와 **[B] 고성능(API Server) 모드** 중 하나를 선택하여 세팅할 수 있습니다.

### 1. 공통 필수 조건 (모든 사용자)
로컬에서 구동할 **초소형 LLM 모델 파일(.gguf)**이 필요합니다.
1. HuggingFace 등에서 양자화된 `.gguf` 파일을 다운로드합니다. (VRAM에 무리가 가지 않는 4B~8B 체급, Q4~Q8 양자화 모델 권장. 예: *Gemma-2-9B, Llama-3-8B* 등)
2. 다운로드한 모델을 ComfyUI 폴더 안의 `models/LLM/` 경로에 넣습니다. (폴더가 없다면 직접 생성해 주세요.)
3. `anima_llm_rewriter.py`와 `__init__.py` 파일을 `ComfyUI/custom_nodes/ComfyUI-Anima-LLM` (이름 자유) 폴더 안에 넣습니다.

### [A] 간편 설치 모드 (Standalone - 일반 유저용)
외부 서버 프로그램 없이 ComfyUI 노드 내에서 직접 모델을 구동하는 방식입니다.
* **선행 조건:** `llama-cpp-python` 패키지 설치 필요.
* **설치 방법 (ComfyUI Portable 기준):**
  1. ComfyUI 최상위 폴더(`run_nvidia_gpu.bat`이 있는 곳)에서 주소창에 `cmd`를 입력하여 터미널을 엽니다.
  2. 다음 명령어를 입력하여 CUDA 가속 버전 패키지를 설치합니다.
     ```cmd
     set CMAKE_ARGS=-DGGML_CUDA=on
     .\python_embeded\python.exe -m pip install llama-cpp-python
     ```
	 
* **사용법:** 노드 설정의 `model_choice`에서 `LLM/모델이름.gguf`를 선택합니다.

### [B] 고성능 하이엔드 모드 (llama-server API - 고급 유저용)
LLM을 독립된 서버 프로세스로 띄워, ComfyUI와의 VRAM 충돌을 완벽히 방지하고 극한의 추론 속도를 내는 방식입니다. (RTX 3090/4090/5090 등 하이엔드 유저 권장)
* **선행 조건:** 공식 [llama.cpp](https://github.com/ggerganov/llama.cpp) 빌드 파일(`llama-server.exe`) 필요.
* **실행 방법:** ComfyUI를 켜기 **전**, 터미널을 열고 서버를 8080 포트로 엽니다. (GPU 레이어 오프로드 `-ngl 99` 권장)
  ```cmd
  llama-server.exe -m "C:\ComfyUI\models\LLM\모델명.gguf" -c 2048 -ngl 99 --port 8080
  

* **사용법:** 노드 설정에서 모델을 `[API] LLAMA-SERVER (127.0.0.1:8080)`으로 선택합니다. (노드가 켜져 있는 서버를 자동 감지하여 API 통신을 수행합니다.)

> 💡 **Tip:** [A] 간편 설치 모드 진행 중 C++ 빌드 툴(Visual Studio) 부재로 에러가 발생한다면, **[B] 고성능 하이엔드 모드(`llama-server` 다운로드 후 실행)**를 사용하는 것이 설치 에러를 피하는 가장 빠르고 확실한 방법입니다.

---

## 💻 사용 방법 (How to Use)

1. ComfyUI를 실행하고 캔버스 빈 공간을 더블 클릭하여 `Anima LLM Prompt Rewriter` 노드를 소환합니다.
2. `enable_llm` 스위치를 **True**로 설정합니다.
3. `model_choice` 드롭다운에서 원하는 `.gguf` 모델이나 API 서버를 선택합니다.
4. 입력 핀에 캐릭터 1, 캐릭터 2, 배경 태그 및 장면(Scene) 묘사를 연결합니다.
5. 출력 핀을 이후의 Text Combine(결합) 노드나 CLIP Text Encode 노드에 연결하여 렌더링(Queue Prompt)을 실행합니다. 진행 상황은 ComfyUI 콘솔(터미널) 창에서 실시간 이모지 로그(🚀, ⏳, ✅)로 확인할 수 있습니다.

---

## 🎛️ 입출력 규격 (Inputs & Outputs)

### 📥 Inputs

| 파라미터명 | 타입 | 설명 |
| --- | --- | --- |
| `enable_llm` | BOOLEAN | LLM 스마트 번역 기능 ON/OFF |
| `manual_prompt` | STRING | LLM 비활성화 시 사용할 수동 입력 텍스트 |
| `model_choice` | COMBO | 사용할 GGUF 모델 선택 또는 API 서버 선택 |
| `temperature` | FLOAT | LLM 창의성 조절 (기본값: 0.1, 번역의 일관성을 위해 낮게 유지 권장) |
| `top_p` | FLOAT | LLM 토큰 샘플링 확률 (기본값: 0.9) |
| `system_prompt` | STRING | LLM에게 부여할 시스템 프롬프트 (번역가 역할 부여) |
| `char_1_tags` / `char_2_tags` | STRING | 캐릭터 1, 2의 단보루 태그 원본 |
| `background_tags` | STRING | 배경 요소 단보루 태그 원본 |
| `scene_and_action` | STRING | 인물간 상호작용 및 상황 묘사 태그 |

### 📤 Outputs

| 핀(Pin) 이름 | 타입 | 설명 |
| --- | --- | --- |
| `final_prompt` | STRING | 완성된 영문 자연어 프롬프트 (LLM OFF 시 `manual_prompt` 출력) |
| `char_1_raw` | STRING | (우회용) 캐릭터 1 원본 태그. LLM 정상 작동 시 공백(`""`) 출력 |
| `char_2_raw` | STRING | (우회용) 캐릭터 2 원본 태그. LLM 정상 작동 시 공백(`""`) 출력 |
| `background_raw` | STRING | (우회용) 배경 원본 태그. LLM 정상 작동 시 공백(`""`) 출력 |

---

## ❓ 자주 묻는 질문 (Troubleshooting)

**Q. 렌더링 중 `Out of Memory (OOM)` 에러가 발생합니다.**

* **A.** Standalone 모드 사용 중 이미지 생성 모델과 LLM 모델이 동시에 VRAM을 차지하여 발생하는 문제입니다. 더 작은 용량의 GGUF 모델(예: Q4 양자화)을 사용하시거나, [B] 고성능 모드(`llama-server`)를 구축하여 VRAM 관리를 독립시키는 것을 강력히 권장합니다.

**Q. 모델 목록(model_choice)에 아무 파일도 뜨지 않습니다.**

* **A.** 다운로드하신 모델이 `ComfyUI/models/LLM` 폴더 안에 정확히 위치해 있는지 확인해 주세요. 파일 확장자는 반드시 소문자 `.gguf`여야 합니다.

**Q. API 서버를 선택했는데 "API 서버가 꺼져 있습니다"라며 우회(Fallback)됩니다.**

* **A.** `llama-server.exe`가 실행된 터미널이 켜져 있는지 확인하세요. 포트 번호가 `8080`인지, 방화벽에서 로컬 루프백(`127.0.0.1`) 접속을 차단하고 있지 않은지 확인해야 합니다.
