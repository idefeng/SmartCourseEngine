#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
本地 LLM 适配器 (Ollama Integration)
=====================================

支持连接本地部署的 Ollama，实现离线课件生成。

支持模型:
- Qwen2.5 (推荐中文)
- Llama3
- Mistral
- 其他 Ollama 支持的模型

作者: SmartCourseEngine Team
日期: 2026-01-31
"""

import os
from typing import Optional, Dict, Any, List

# ============================================================================
# 配置
# ============================================================================
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
DEFAULT_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")


# ============================================================================
# Ollama 适配器
# ============================================================================
class OllamaAdapter:
    """
    Ollama 本地 LLM 适配器
    
    提供与 OpenAI API 兼容的接口。
    """
    
    def __init__(
        self,
        host: str = OLLAMA_HOST,
        model: str = DEFAULT_MODEL
    ):
        """
        初始化 Ollama 适配器
        
        Args:
            host: Ollama 服务地址
            model: 模型名称
        """
        self.host = host.rstrip('/')
        self.model = model
        self.client = None
        
        self._init_client()
    
    def _init_client(self):
        """初始化 Ollama 客户端"""
        try:
            import ollama
            self.client = ollama.Client(host=self.host)
            print(f"✅ Ollama 连接成功: {self.host}")
        except ImportError:
            print("⚠️ ollama 库未安装，请运行: pip install ollama")
        except Exception as e:
            print(f"⚠️ Ollama 连接失败: {e}")
    
    def is_available(self) -> bool:
        """检查 Ollama 是否可用"""
        if not self.client:
            return False
        
        try:
            self.client.list()
            return True
        except Exception:
            return False
    
    def list_models(self) -> List[Dict]:
        """
        列出可用模型
        
        Returns:
            模型列表
        """
        if not self.client:
            return []
        
        try:
            response = self.client.list()
            return response.get("models", [])
        except Exception as e:
            print(f"获取模型列表失败: {e}")
            return []
    
    def pull_model(self, model_name: str) -> bool:
        """
        拉取模型
        
        Args:
            model_name: 模型名称
            
        Returns:
            是否成功
        """
        if not self.client:
            return False
        
        try:
            print(f"📥 正在拉取模型: {model_name}...")
            self.client.pull(model_name)
            print(f"✅ 模型拉取完成: {model_name}")
            return True
        except Exception as e:
            print(f"❌ 模型拉取失败: {e}")
            return False
    
    def generate(
        self,
        prompt: str,
        system: str = None,
        temperature: float = 0.7,
        max_tokens: int = 2048
    ) -> str:
        """
        生成文本
        
        Args:
            prompt: 用户提示
            system: 系统提示
            temperature: 温度参数
            max_tokens: 最大 token 数
            
        Returns:
            生成的文本
        """
        if not self.client:
            raise RuntimeError("Ollama 客户端未初始化")
        
        messages = []
        
        if system:
            messages.append({"role": "system", "content": system})
        
        messages.append({"role": "user", "content": prompt})
        
        try:
            response = self.client.chat(
                model=self.model,
                messages=messages,
                options={
                    "temperature": temperature,
                    "num_predict": max_tokens
                }
            )
            
            return response["message"]["content"]
            
        except Exception as e:
            raise RuntimeError(f"Ollama 生成失败: {e}")
    
    def invoke(self, prompt: str) -> "OllamaResponse":
        """
        LangChain 兼容的调用接口
        
        Args:
            prompt: 提示文本
            
        Returns:
            响应对象
        """
        content = self.generate(prompt)
        return OllamaResponse(content=content)
    
    def embed(self, texts: List[str]) -> List[List[float]]:
        """
        生成 Embedding
        
        Args:
            texts: 文本列表
            
        Returns:
            Embedding 向量列表
        """
        if not self.client:
            raise RuntimeError("Ollama 客户端未初始化")
        
        embeddings = []
        
        for text in texts:
            try:
                response = self.client.embeddings(
                    model=self.model,
                    prompt=text
                )
                embeddings.append(response["embedding"])
            except Exception as e:
                print(f"Embedding 生成失败: {e}")
                embeddings.append([0.0] * 768)  # 默认维度
        
        return embeddings


class OllamaResponse:
    """Ollama 响应对象，兼容 LangChain"""
    
    def __init__(self, content: str):
        self.content = content
    
    def __str__(self):
        return self.content


# ============================================================================
# LangChain 兼容适配器
# ============================================================================
class OllamaLLM:
    """
    LangChain 兼容的 Ollama LLM 包装器
    """
    
    def __init__(
        self,
        host: str = OLLAMA_HOST,
        model: str = DEFAULT_MODEL,
        temperature: float = 0.7
    ):
        self.adapter = OllamaAdapter(host=host, model=model)
        self.temperature = temperature
    
    def invoke(self, prompt: str) -> OllamaResponse:
        """调用 LLM"""
        content = self.adapter.generate(
            prompt,
            temperature=self.temperature
        )
        return OllamaResponse(content=content)
    
    def __call__(self, prompt: str) -> str:
        """直接调用"""
        return self.adapter.generate(prompt, temperature=self.temperature)


# ============================================================================
# 工厂函数
# ============================================================================
def create_llm(
    use_local: bool = False,
    local_host: str = OLLAMA_HOST,
    local_model: str = DEFAULT_MODEL,
    api_key: str = None,
    api_base: str = None,
    model_name: str = None,
    temperature: float = 0.7
):
    """
    创建 LLM 实例
    
    Args:
        use_local: 是否使用本地 Ollama
        local_host: Ollama 服务地址
        local_model: Ollama 模型名称
        api_key: OpenAI 兼容 API Key
        api_base: API 基础 URL
        model_name: 模型名称
        temperature: 温度参数
        
    Returns:
        LLM 实例
    """
    if use_local:
        adapter = OllamaAdapter(host=local_host, model=local_model)
        
        if adapter.is_available():
            return OllamaLLM(
                host=local_host,
                model=local_model,
                temperature=temperature
            )
        else:
            print("⚠️ Ollama 不可用，回退到云端 API")
    
    # 使用云端 API
    from langchain_openai import ChatOpenAI
    
    return ChatOpenAI(
        api_key=api_key or os.getenv("DEEPSEEK_API_KEY"),
        base_url=api_base or os.getenv("API_BASE_URL", "https://api.deepseek.com/v1"),
        model=model_name or os.getenv("MODEL_NAME", "deepseek-chat"),
        temperature=temperature
    )


# ============================================================================
# 测试
# ============================================================================
if __name__ == "__main__":
    print("🔍 测试 Ollama 连接...")
    
    adapter = OllamaAdapter()
    
    if adapter.is_available():
        print("✅ Ollama 可用")
        
        models = adapter.list_models()
        print(f"📋 可用模型: {[m.get('name') for m in models]}")
        
        # 测试生成
        print("\n🧪 测试生成...")
        response = adapter.generate("你好，请用一句话介绍自己")
        print(f"响应: {response}")
    else:
        print("❌ Ollama 不可用")
