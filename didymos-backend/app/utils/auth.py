"""
Authentication utilities
"""

def get_user_id_from_token(token: str) -> str:
    """
    토큰에서 사용자 ID 추출

    MVP: 토큰 = user_id (단순 passthrough)
    TODO: JWT 검증 구현 필요 (프로덕션 전 필수)

    Args:
        token: 사용자 토큰 (현재는 user_id와 동일)

    Returns:
        사용자 ID
    """
    # TODO: JWT 검증 로직 추가
    # - 토큰 서명 검증
    # - 만료 시간 확인
    # - 클레임 추출
    return token
