#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
sys.path.append(os.path.dirname(__file__))

# 直接导入模块
import instr_rewrite_1
build_prompt = instr_rewrite_1.build_prompt
load_app_data = instr_rewrite_1.load_app_data

def test_optimized_code():
    """测试优化后的代码"""
    try:
        # 加载app数据
        app_data = load_app_data()
        print(f"成功加载 {len(app_data)} 个app数据")

        # 测试不同类型的用户指令
        test_instructions = [
            "帮我找一本历史小说",
            "记录今天的会议笔记",
            "搜索天气预报",
            "计划周末旅行",
            "分享照片到微信",
            "买一台游戏笔记本",
            "看一部科幻电影",
            "计算购物总价"
        ]

        for instruction in test_instructions:
            try:
                prompt = build_prompt(instruction, app_data)
                print(f"✓ 指令 '{instruction}' 处理成功，prompt长度: {len(prompt)}")
            except Exception as e:
                print(f"✗ 指令 '{instruction}' 处理失败: {e}")

        print("\n所有测试完成！")

    except Exception as e:
        print(f"测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_optimized_code()
