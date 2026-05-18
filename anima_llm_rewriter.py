import os
import glob
import json
import urllib.request
import urllib.error
import gc
import folder_paths

try:
    import torch
except ImportError:
    pass

if "LLM" not in folder_paths.folder_names_and_paths:
    llm_path = os.path.join(folder_paths.models_dir, "LLM")
    if not os.path.exists(llm_path):
        os.makedirs(llm_path, exist_ok=True)
    folder_paths.add_model_folder_path("LLM", llm_path)

# ==============================================================================
# 🛠️ [개선] UI 표기용 이름과 실제 절대 경로를 매핑하는 글로벌 딕셔너리
# ==============================================================================
MODEL_PATH_MAP = {}


def get_model_list():
    global MODEL_PATH_MAP
    MODEL_PATH_MAP.clear() # 갱신 시 초기화
    
    api_key = "[API] LLAMA-SERVER (127.0.0.1:8080)"
    display_names = [api_key]
    MODEL_PATH_MAP[api_key] = api_key # API는 경로가 동일

    llm_paths = folder_paths.get_folder_paths("LLM")
    
    for base_path in llm_paths:
        if os.path.exists(base_path):
            for filepath in glob.glob(os.path.join(base_path, '**', '*.gguf'), recursive=True):
                # 1. 원본 파일명 추출 (예: gemma.gguf)
                filename = os.path.basename(filepath)
                
                # 2. 부모 폴더 구조 포함 여부 (선택)
                # 만약 LLM 폴더 바로 아래가 아니라 LLM/Gemma/ 폴더 안에 있다면 
                # "Gemma/gemma.gguf" 처럼 나오게 하려면 아래처럼 상대 경로를 씁니다.
                rel_path = os.path.relpath(filepath, base_path) 
                
                # 3. UI에 보여줄 최종 이름 생성 (예: "LLM/gemma.gguf")
                display_name = f"LLM/{rel_path}".replace("\\", "/") # 윈도우 역슬래시 통일
                
                # 4. 리스트에 추가 및 매핑 딕셔너리 저장
                display_names.append(display_name)
                MODEL_PATH_MAP[display_name] = filepath 

    return display_names

def is_server_running(url="http://127.0.0.1:8080/health"):
    try:
        req = urllib.request.Request(url, method='GET')
        with urllib.request.urlopen(req, timeout=0.5) as response:
            return response.status == 200
    except:
        return False

class AnimaLLMPromptRewriterHybrid:
    """
    단보루 태그를 자연어로 변환하는 하이브리드 노드입니다.
    """
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "enable_llm": ("BOOLEAN", {"default": True}), 
                "manual_prompt": ("STRING", {"multiline": True, "default": ""}),
                
                # UI에는 짧고 깔끔한 이름만 노출됩니다.
                "model_choice": (get_model_list(), ),
                
                "temperature": ("FLOAT", {"default": 0.1, "min": 0.0, "max": 2.0, "step": 0.05}),
                "top_p": ("FLOAT", {"default": 0.9, "min": 0.0, "max": 1.0, "step": 0.05}),
                
                "system_prompt": ("STRING", {"multiline": True, "default": "You are a strict prompt translator..."}),
                
                "char_1_tags": ("STRING", {"multiline": True, "default": ""}),
                "char_2_tags": ("STRING", {"multiline": True, "default": ""}),
                "background_tags": ("STRING", {"multiline": True, "default": ""}),
                "scene_and_action": ("STRING", {"multiline": True, "default": ""}),
            }
        }

    RETURN_TYPES = ("STRING", "STRING", "STRING", "STRING")
    RETURN_NAMES = ("final_prompt", "char_1_raw", "char_2_raw", "background_raw")
    FUNCTION = "rewrite_prompt"
    CATEGORY = "Anima Generator/Text"
    OUTPUT_NODE = True  # 🌟 [수술] 프론트엔드 UI 전송을 위한 필수 플래그 주입
        
    def rewrite_prompt(self, enable_llm, manual_prompt, model_choice, temperature, top_p, system_prompt, char_1_tags, char_2_tags, background_tags, scene_and_action):
        
        # ==============================================================================
        # 🛠️ [개선] UI에서 선택한 짧은 이름을 내부적으로 진짜 절대 경로로 변환 (경로 복원)
        # ==============================================================================
        actual_model_path = MODEL_PATH_MAP.get(model_choice, model_choice)
        
        print(f"\n[Anima LLM Hybrid] 🚀 프롬프트 처리 시작 (LLM 모드: {'ON' if enable_llm else 'OFF'})")

        char_1_out = char_1_tags.strip() if char_1_tags and char_1_tags.strip() else ""
        char_2_out = char_2_tags.strip() if char_2_tags and char_2_tags.strip() else ""
        bg_out = background_tags.strip() if background_tags and background_tags.strip() else ""

        if not enable_llm:
            print("[Anima LLM Hybrid] ⚠️ LLM OFF: 수동 우회(Bypass)합니다.\n")
            return {"ui": {"text": [manual_prompt]}, "result": (manual_prompt, char_1_out, char_2_out, bg_out)}

        raw_tags_list = []
        if char_1_out: raw_tags_list.append(char_1_out)
        if char_2_out: raw_tags_list.append(char_2_out)
        if bg_out: raw_tags_list.append(bg_out)
        if scene_and_action and scene_and_action.strip(): raw_tags_list.append(scene_and_action.strip())

        user_prompt_parts = []
        if char_1_out: user_prompt_parts.append(f"Character 1 Tags: {char_1_out}")
        if char_2_out: user_prompt_parts.append(f"Character 2 Tags: {char_2_out}")
        if bg_out: user_prompt_parts.append(f"Background Tags: {bg_out}")
        if scene_and_action and scene_and_action.strip(): user_prompt_parts.append(f"Scene & Action Tags: {scene_and_action.strip()}")
            
        user_prompt = "\n".join(user_prompt_parts)

        server_alive = is_server_running()
        is_api_mode = False

        if server_alive:
            print("[Anima LLM Hybrid] 🟢 백그라운드에서 llama-server 구동을 감지했습니다.")
            if model_choice != "[API] LLAMA-SERVER (127.0.0.1:8080)":
                print("[Anima LLM Hybrid] 🛡️ [안전장치 발동] VRAM 충돌(OOM) 방지를 위해 선택하신 로컬 모델 대신 API 통신으로 강제 전환합니다.")
            is_api_mode = True
        else:
            if model_choice == "[API] LLAMA-SERVER (127.0.0.1:8080)":
                print("\n[Anima LLM Hybrid] ❌ 에러: API 서버가 꺼져 있습니다. 우회 파이프라인을 가동합니다.\n")
                fallback = manual_prompt if manual_prompt and manual_prompt.strip() else ", ".join(raw_tags_list)
                # 🌟 [수술] 리턴 규격 수정
                return {"ui": {"text": [fallback]}, "result": (fallback, char_1_out, char_2_out, bg_out)}
            else:
                print("[Anima LLM Hybrid] 🔴 API 서버가 꺼져 있으므로 Standalone (로컬 로드) 모드로 진입합니다.")
                is_api_mode = False

        if is_api_mode:
            print(f"[Anima LLM Hybrid] ⏳ llama-server에 번역을 요청 중입니다...")
            payload = {
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "temperature": temperature,
                "top_p": top_p,
                "stream": False
            }
            
            try:
                req = urllib.request.Request(
                    "http://127.0.0.1:8080/v1/chat/completions", 
                    data=json.dumps(payload).encode('utf-8'), 
                    headers={'Content-Type': 'application/json'}
                )
                with urllib.request.urlopen(req) as response:
                    result = json.loads(response.read().decode('utf-8'))
                    generated_text = result["choices"][0]["message"]["content"].strip()
                    
                    if not generated_text:
                        raise ValueError("LLM returned an empty string.")
                        
                    print(f"[Anima LLM Hybrid] ✅ API 번역 완료! (출력 길이: {len(generated_text)}자)\n")
                    # 🌟 [수술] 리턴 규격 수정
                    return {"ui": {"text": [generated_text]}, "result": (generated_text, "", "", "")}
                    
            except Exception as e:
                print(f"\n[Anima LLM Hybrid] ❌ API 통신 중 에러 발생: {str(e)}")
                print("[Anima LLM Hybrid] ⚠️ 우회(Fallback) 파이프라인을 가동합니다.\n")
                fallback = manual_prompt if manual_prompt and manual_prompt.strip() else ", ".join(raw_tags_list)
                # 🌟 [수술] 리턴 규격 수정
                return {"ui": {"text": [fallback]}, "result": (fallback, char_1_out, char_2_out, bg_out)}

        else:
            # 🛠️ [적용] UI 이름이 아닌 복원된 진짜 경로(actual_model_path)를 llama.cpp에 넘겨줍니다.
            print(f"[Anima LLM Hybrid] ⏳ 모델 로딩 및 VRAM 할당 중... ({model_choice})")
            try:
                from llama_cpp import Llama
                
                llm = Llama(
                    model_path=actual_model_path, # 여기서 변환된 경로를 사용!
                    n_gpu_layers=-1, 
                    n_ctx=2048,
                    verbose=False
                )
                
                print(f"[Anima LLM Hybrid] 🧠 자연어 프롬프트 생성 중...")
                response = llm.create_chat_completion(
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=temperature,
                    top_p=top_p
                )
                
                generated_text = response["choices"][0]["message"]["content"].strip()
                
                if not generated_text:
                    raise ValueError("LLM returned an empty string.")

                print(f"[Anima LLM Hybrid] ✅ Standalone 번역 완료! (출력 길이: {len(generated_text)}자)")

            except Exception as e:
                print(f"\n[Anima LLM Hybrid] ❌ Standalone 처리 중 에러 발생: {str(e)}")
                print("[Anima LLM Hybrid] ⚠️ 우회(Fallback) 파이프라인 가동.\n")
                generated_text = manual_prompt if manual_prompt and manual_prompt.strip() else ", ".join(raw_tags_list)
                error_fallback = True
            else:
                error_fallback = False

            print(f"[Anima LLM Hybrid] 🧹 이미지 생성을 위해 LLM을 VRAM에서 즉시 해제합니다...\n")
            if 'llm' in locals():
                del llm
            gc.collect()
            try:
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
            except NameError:
                pass

            if error_fallback:
                # 🌟 [수술] 리턴 규격 수정
                return {"ui": {"text": [generated_text]}, "result": (generated_text, char_1_out, char_2_out, bg_out)}
                 
            # 🌟 [수술] 리턴 규격 수정
            return {"ui": {"text": [generated_text]}, "result": (generated_text, "", "", "")}

NODE_CLASS_MAPPINGS = {
    "AnimaLLMPromptRewriterHybrid": AnimaLLMPromptRewriterHybrid
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "AnimaLLMPromptRewriterHybrid": "Anima LLM Prompt Rewriter"
}