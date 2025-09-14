#!/usr/bin/env python3
"""
Git 환경 설정 스크립트

PowerShell에서 발생하는 Git 문제를 해결하기 위한 환경 설정을 수행합니다.
"""

import subprocess
import sys


def run_git_config(config_name, config_value):
    """Git 설정을 적용합니다."""
    try:
        command = f'git config --global {config_name} "{config_value}"'
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"✅ {config_name} = {config_value}")
            return True
        else:
            print(f"❌ {config_name} 설정 실패: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ {config_name} 설정 중 오류: {e}")
        return False


def setup_git_for_windows():
    """Windows PowerShell 환경에 최적화된 Git 설정을 적용합니다."""
    print("🔧 Windows PowerShell용 Git 환경 설정 시작...")
    
    configs = [
        # Pager 문제 해결
        ("core.pager", "cat"),
        
        # Windows CRLF 처리
        ("core.autocrlf", "true"),
        
        # 에디터 설정 (메모장 사용)
        ("core.editor", "notepad"),
        
        # 긴 경로 지원
        ("core.longpaths", "true"),
        
        # 유니코드 지원
        ("core.quotepath", "false"),
        
        # 커밋 템플릿 비활성화 (PowerShell 호환성)
        ("commit.cleanup", "strip"),
        
        # 푸시 기본 브랜치 설정
        ("push.default", "simple"),
        
        # 색상 출력 활성화
        ("color.ui", "auto"),
    ]
    
    success_count = 0
    for config_name, config_value in configs:
        if run_git_config(config_name, config_value):
            success_count += 1
    
    print(f"\n📊 설정 완료: {success_count}/{len(configs)}개 항목")
    
    if success_count == len(configs):
        print("🎉 모든 Git 설정이 완료되었습니다!")
        print("\n📋 적용된 설정:")
        print("   - Pager 비활성화 (cat 사용)")
        print("   - Windows CRLF 자동 변환")
        print("   - 메모장 에디터 사용")
        print("   - 긴 경로명 지원")
        print("   - 유니코드 파일명 지원")
        print("   - PowerShell 호환 커밋 정리")
        
        print("\n💡 사용법:")
        print("   기존: git commit -m '긴 메시지...'")
        print("   개선: python git_helper.py auto '간단한 메시지'")
        
        return True
    else:
        print("⚠️ 일부 설정이 실패했습니다. 수동으로 확인해주세요.")
        return False


def check_current_config():
    """현재 Git 설정을 확인합니다."""
    print("📋 현재 Git 설정:")
    
    configs_to_check = [
        "user.name",
        "user.email", 
        "core.pager",
        "core.autocrlf",
        "core.editor",
        "core.longpaths",
        "core.quotepath",
        "push.default"
    ]
    
    for config in configs_to_check:
        try:
            result = subprocess.run(
                f"git config --global {config}", 
                shell=True, 
                capture_output=True, 
                text=True
            )
            
            if result.returncode == 0:
                value = result.stdout.strip()
                print(f"   {config} = {value}")
            else:
                print(f"   {config} = (설정되지 않음)")
        except:
            print(f"   {config} = (확인 실패)")


def main():
    """메인 실행 함수"""
    if len(sys.argv) > 1 and sys.argv[1] == "check":
        check_current_config()
    else:
        setup_git_for_windows()
        print("\n" + "="*50)
        check_current_config()


if __name__ == "__main__":
    main()
