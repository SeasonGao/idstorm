"""
DeepSeek API 连通性测试脚本

测试内容：
  1. 默认配置（无 timeout/max_retries）下的连通性
  2. 带 timeout=60.0, max_retries=1 配置下的连通性
  3. 多轮快速请求，观察稳定性
"""

import time
import asyncio
from openai import OpenAI

API_KEY = "sk-71082a31675d442aa21191d5826427e8"
BASE_URL = "https://api.deepseek.com"
MODEL = "deepseek-v4-flash"


def test_basic():
    print("=" * 60)
    print("[Test 1] 默认配置 + timeout=30s（原代码无 timeout 会无限等待）")
    print("=" * 60)
    client = OpenAI(api_key=API_KEY, base_url=BASE_URL, timeout=30.0)
    start = time.time()
    try:
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": "你好，请用一句话回复"}],
            max_tokens=100,
            temperature=0.1,
            extra_body={"thinking": {"type": "disabled"}},
        )
        elapsed = time.time() - start
        content = resp.choices[0].message.content
        print(f"  ✅ 成功  |  耗时: {elapsed:.2f}s  |  回复: {content[:80]}")
    except Exception as e:
        elapsed = time.time() - start
        print(f"  ❌ 失败  |  耗时: {elapsed:.2f}s  |  错误: {type(e).__name__}: {e}")
    print()


def test_with_timeout():
    print("=" * 60)
    print("[Test 2] 配置 timeout=60.0, max_retries=1")
    print("=" * 60)
    client = OpenAI(api_key=API_KEY, base_url=BASE_URL, timeout=60.0, max_retries=1)
    start = time.time()
    try:
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": "你好，请用一句话回复"}],
            max_tokens=100,
            temperature=0.1,
            extra_body={"thinking": {"type": "disabled"}},
        )
        elapsed = time.time() - start
        content = resp.choices[0].message.content
        print(f"  ✅ 成功  |  耗时: {elapsed:.2f}s  |  回复: {content[:80]}")
    except Exception as e:
        elapsed = time.time() - start
        print(f"  ❌ 失败  |  耗时: {elapsed:.2f}s  |  错误: {e}")
    print()


def test_stability():
    print("=" * 60)
    print("[Test 3] 连续 5 次快速请求（模拟 dialogue_engine 多节点调用）")
    print("=" * 60)
    client = OpenAI(api_key=API_KEY, base_url=BASE_URL, timeout=60.0, max_retries=1)
    prompts = [
        "请用JSON格式回复: {\"decision\": \"continue\", \"reason\": \"测试\"}",
        "请生成一个关于产品设计的提问，不超过20字",
        "请用JSON格式回复: {\"options\": [\"选项A\", \"选项B\", \"选项C\"]}",
        "请总结以下内容：这是一个智能开关产品设计",
        "请用一句话描述现代工业设计的特点",
    ]
    ok = 0
    fail = 0
    for i, prompt in enumerate(prompts):
        start = time.time()
        try:
            resp = client.chat.completions.create(
                model=MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=200,
                temperature=0.1,
                extra_body={"thinking": {"type": "disabled"}},
            )
            elapsed = time.time() - start
            content = resp.choices[0].message.content
            ok += 1
            print(f"  [{i+1}/5] ✅ {elapsed:.2f}s | {content[:60]}")
        except Exception as e:
            elapsed = time.time() - start
            fail += 1
            print(f"  [{i+1}/5] ❌ {elapsed:.2f}s | {e}")
    print(f"\n  结果: {ok} 成功 / {fail} 失败")
    print()


def test_async():
    print("=" * 60)
    print("[Test 4] 模拟 dialogue_engine 的 asyncio.to_thread 调用方式")
    print("=" * 60)

    async def _call():
        def _sync():
            client = OpenAI(
                api_key=API_KEY,
                base_url=BASE_URL,
                timeout=60.0,
                max_retries=1,
            )
            return client.chat.completions.create(
                model=MODEL,
                messages=[{"role": "user", "content": "你好，请用一句话回复"}],
                max_tokens=100,
                temperature=0.1,
                extra_body={"thinking": {"type": "disabled"}},
            )

        start = time.time()
        try:
            response = await asyncio.to_thread(_sync)
            elapsed = time.time() - start
            content = response.choices[0].message.content
            print(f"  ✅ 成功  |  耗时: {elapsed:.2f}s  |  回复: {content[:80]}")
        except Exception as e:
            elapsed = time.time() - start
            print(f"  ❌ 失败  |  耗时: {elapsed:.2f}s  |  错误: {e}")

    asyncio.run(_call())
    print()


if __name__ == "__main__":
    test_basic()
    test_with_timeout()
    test_stability()
    test_async()
    print("测试完成。")
