#!/usr/bin/env python3
"""
Git 헬퍼 스크립트

PowerShell에서 발생하는 Git 커밋 문제를 해결하기 위한 도구입니다.
"""

import subprocess
import sys
import os
from datetime import datetime


def run_command(command, capture_output=True):
    """명령어를 실행하고 결과를 반환합니다."""
    try:
        if capture_output:
            result = subprocess.run(
                command, 
                shell=True, 
                capture_output=True, 
                text=True, 
                encoding='utf-8'
            )
            return result.returncode == 0, result.stdout.strip(), result.stderr.strip()
        else:
            result = subprocess.run(command, shell=True)
            return result.returncode == 0, "", ""
    except Exception as e:
        return False, "", str(e)


def git_status():
    """Git 상태를 확인합니다."""
    success, stdout, stderr = run_command("git status --porcelain")
    if not success:
        print(f"❌ Git 상태 확인 실패: {stderr}")
        return False
    
    if stdout.strip():
        print("📁 변경된 파일들:")
        for line in stdout.split('\n'):
            if line.strip():
                print(f"   {line}")
        return True
    else:
        print("✅ 변경사항이 없습니다.")
        return False


def git_add_all():
    """모든 변경사항을 스테이징합니다."""
    success, stdout, stderr = run_command("git add .")
    if success:
        print("✅ 모든 파일이 스테이징되었습니다.")
        return True
    else:
        print(f"❌ 파일 스테이징 실패: {stderr}")
        return False


def git_commit_simple(message):
    """간단한 커밋 메시지로 커밋합니다."""
    # 특수문자 제거 및 길이 제한
    clean_message = message.replace('"', "'").replace('\n', ' ').replace('\r', '')
    if len(clean_message) > 100:
        clean_message = clean_message[:97] + "..."
    
    # 단일 라인 커밋 명령어
    command = f'git commit -m "{clean_message}"'
    success, stdout, stderr = run_command(command)
    
    if success:
        print(f"✅ 커밋 완료: {clean_message}")
        return True
    else:
        print(f"❌ 커밋 실패: {stderr}")
        return False


def git_push():
    """원격 저장소에 푸시합니다."""
    success, stdout, stderr = run_command("git push origin main")
    if success:
        print("✅ GitHub에 푸시 완료")
        return True
    else:
        print(f"❌ 푸시 실패: {stderr}")
        return False


def git_log_simple():
    """간단한 로그를 출력합니다."""
    success, stdout, stderr = run_command("git log --oneline -10")
    if success:
        print("📜 최근 커밋 로그:")
        for line in stdout.split('\n'):
            if line.strip():
                print(f"   {line}")
    else:
        print(f"❌ 로그 조회 실패: {stderr}")


def main():
    """메인 실행 함수"""
    if len(sys.argv) < 2:
        print("🤖 Git 헬퍼 사용법:")
        print("   python git_helper.py status      - Git 상태 확인")
        print("   python git_helper.py add         - 모든 파일 스테이징")
        print("   python git_helper.py commit 'message' - 커밋 실행")
        print("   python git_helper.py push        - GitHub 푸시")
        print("   python git_helper.py log         - 커밋 로그 확인")
        print("   python git_helper.py auto 'message' - 자동 커밋+푸시")
        return
    
    command = sys.argv[1].lower()
    
    if command == "status":
        git_status()
    
    elif command == "add":
        if git_status():
            git_add_all()
        else:
            print("변경사항이 없어 스테이징할 파일이 없습니다.")
    
    elif command == "commit":
        if len(sys.argv) < 3:
            print("❌ 커밋 메시지를 입력해주세요.")
            print("   예: python git_helper.py commit 'feat: 새로운 기능 추가'")
            return
        
        message = sys.argv[2]
        git_commit_simple(message)
    
    elif command == "push":
        git_push()
    
    elif command == "log":
        git_log_simple()
    
    elif command == "auto":
        if len(sys.argv) < 3:
            print("❌ 커밋 메시지를 입력해주세요.")
            print("   예: python git_helper.py auto 'feat: 새로운 기능 추가'")
            return
        
        message = sys.argv[2]
        print("🚀 자동 Git 워크플로우 시작...")
        
        # 1. 상태 확인
        if not git_status():
            print("변경사항이 없어 커밋할 내용이 없습니다.")
            return
        
        # 2. 스테이징
        if not git_add_all():
            return
        
        # 3. 커밋
        if not git_commit_simple(message):
            return
        
        # 4. 푸시
        if not git_push():
            return
        
        print("🎉 모든 작업이 완료되었습니다!")
        git_log_simple()
    
    else:
        print(f"❌ 알 수 없는 명령어: {command}")


if __name__ == "__main__":
    main()
