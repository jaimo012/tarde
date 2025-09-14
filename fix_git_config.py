#!/usr/bin/env python3
"""
Git 설정 문제 해결 스크립트
PowerShell 호환성 및 pager 문제 해결
"""

import subprocess
import sys
import os
from pathlib import Path

def run_command(cmd, description):
    """명령어 실행 및 결과 출력"""
    print(f"🔧 {description}...")
    try:
        result = subprocess.run(
            cmd, 
            shell=True, 
            capture_output=True, 
            text=True, 
            encoding='utf-8'
        )
        
        if result.returncode == 0:
            print(f"✅ 성공: {description}")
            if result.stdout.strip():
                print(f"   출력: {result.stdout.strip()}")
        else:
            print(f"❌ 실패: {description}")
            print(f"   오류: {result.stderr.strip()}")
        
        return result.returncode == 0
        
    except Exception as e:
        print(f"❌ 예외 발생: {e}")
        return False

def main():
    print("🚀 Git 설정 문제 해결 시작...")
    print("=" * 50)
    
    # Git 설정 변경
    configs = [
        ("git config --global core.pager \"\"", "Git pager 비활성화"),
        ("git config --global core.editor \"notepad\"", "기본 에디터를 메모장으로 설정"),
        ("git config --global core.autocrlf true", "Windows 줄바꿈 처리 설정"),
        ("git config --global core.quotepath false", "한글 파일명 처리 설정"),
        ("git config --global i18n.commitencoding utf-8", "커밋 메시지 인코딩 설정"),
        ("git config --global i18n.logoutputencoding utf-8", "로그 출력 인코딩 설정"),
    ]
    
    success_count = 0
    for cmd, desc in configs:
        if run_command(cmd, desc):
            success_count += 1
    
    print("\n" + "=" * 50)
    print(f"📊 결과: {success_count}/{len(configs)} 설정 완료")
    
    # 현재 Git 설정 확인
    print("\n🔍 현재 Git 설정 확인:")
    print("-" * 30)
    
    check_configs = [
        "git config --global --get core.pager",
        "git config --global --get core.editor", 
        "git config --global --get core.autocrlf",
        "git config --global --get user.name",
        "git config --global --get user.email"
    ]
    
    for cmd in check_configs:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        config_name = cmd.split('.')[-1]
        value = result.stdout.strip() if result.stdout.strip() else "설정되지 않음"
        print(f"  {config_name}: {value}")
    
    print("\n✅ Git 설정 수정 완료!")
    print("이제 Git 명령어가 PowerShell에서 정상 동작할 것입니다.")

if __name__ == "__main__":
    main()
