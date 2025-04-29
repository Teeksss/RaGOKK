# Last reviewed: 2025-04-29 07:20:15 UTC (User: Teeksss)
import requests
import json
import asyncio
import httpx
from typing import List, Dict, Optional
from fastapi import HTTPException, Request, status
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from .config import (
    TWITTER_CLIENT_ID,
    TWITTER_CLIENT_SECRET,
    TWITTER_REDIRECT_URI,
    FACEBOOK_API_VERSION,
    FACEBOOK_APP_ID,
    FACEBOOK_APP_SECRET,
    FACEBOOK_REDIRECT_URI,
    LINKEDIN_API_VERSION_DATE
)
from .token_store import save_oauth_state_to_session, validate_oauth_state_from_session, save_token_db, load_token_db
from .logger import get_logger

logger = get_logger(__name__)

# --- Twitter Fonksiyonları ---
def start_twitter_auth_flow(request: Request, user_id: str) -> str:
    """Twitter OAuth 2.0 yetkilendirme akışını başlatır"""
    if not all([TWITTER_CLIENT_ID, TWITTER_CLIENT_SECRET, TWITTER_REDIRECT_URI]):
        logger.error("Twitter OAuth ayarları eksik.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Twitter OAuth ayarları eksik."
        )
    
    try:
        # CSRF koruması için OAuth state oluştur
        state = save_oauth_state_to_session(request, user_id, 'twitter')
        
        # PKCE Code Challenge oluştur
        code_verifier = secrets.token_urlsafe(32)
        # Code challenge'ı sakla
        request.session["twitter_code_verifier"] = code_verifier
        
        # Twitter auth URL'ini oluştur (OAuth 2.0)
        auth_url = (
            f"https://twitter.com/i/oauth2/authorize"
            f"?client_id={TWITTER_CLIENT_ID}"
            f"&response_type=code"
            f"&redirect_uri={TWITTER_REDIRECT_URI}"
            f"&scope=tweet.read%20users.read"
            f"&state={state}"
            f"&code_challenge={code_verifier}"
            f"&code_challenge_method=plain"
        )
        
        logger.info(f"Twitter yetkilendirme URL'si oluşturuldu (User ID: {user_id}).")
        return auth_url
    except Exception as e:
        logger.error(f"Twitter yetkilendirme başlatılamadı (User ID: {user_id}): {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Twitter yetkilendirme başlatılamadı."
        )

async def complete_twitter_auth_flow(request: Request, state: str, code: str, db: Session):
    """Twitter OAuth callback'i işler ve token alır/saklar"""
    validated_data = validate_oauth_state_from_session(request, state)
    if not validated_data:
        logger.warning("Geçersiz Twitter OAuth state.")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Geçersiz OAuth state."
        )
    
    user_id = int(validated_data['user_id'])
    
    if not all([TWITTER_CLIENT_ID, TWITTER_CLIENT_SECRET, TWITTER_REDIRECT_URI]):
        logger.error("Twitter OAuth ayarları eksik.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Twitter OAuth ayarları eksik."
        )
    
    # Code verifier'ı session'dan al
    code_verifier = request.session.pop("twitter_code_verifier", "")
    if not code_verifier:
        logger.warning("Twitter code_verifier oturumda bulunamadı.")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Oturum verisi eksik."
        )
    
    try:
        # Token al
        async with httpx.AsyncClient(timeout=30.0) as client:
            token_response = await client.post(
                "https://api.twitter.com/2/oauth2/token",
                data={
                    "code": code,
                    "grant_type": "authorization_code",
                    "client_id": TWITTER_CLIENT_ID,
                    "redirect_uri": TWITTER_REDIRECT_URI,
                    "code_verifier": code_verifier
                },
                auth=(TWITTER_CLIENT_ID, TWITTER_CLIENT_SECRET)
            )
        
        if token_response.status_code != 200:
            logger.error(f"Twitter token hatası: {token_response.text}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Twitter token alınamadı: {token_response.text}"
            )
        
        token_data = token_response.json()
        
        # Expires_at ekle
        if "expires_in" in token_data:
            expires_at = datetime.utcnow() + timedelta(seconds=int(token_