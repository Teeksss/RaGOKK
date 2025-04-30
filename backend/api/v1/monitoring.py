# Last reviewed: 2025-04-30 08:16:40 UTC (User: Teeksss)
from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import Dict, Any, List, Optional
import logging

from ...auth.rbac import require_permission, Permission, require_role, Role
from ...auth.enhanced_jwt import get_current_user_enhanced
from ...core.monitoring import MonitoringService

router = APIRouter(prefix="/monitoring", tags=["monitoring"])
logger = logging.getLogger(__name__)

# Monitoring servisini başlat
monitoring_service = MonitoringService()

@router.get("/metrics", dependencies=[Depends(require_permission(Permission.VIEW_ANALYTICS))])
async def get_current_metrics():
    """
    Mevcut sistem metriklerini döndürür.
    
    Requires:
        - `view:analytics` permission
    """
    return monitoring_service.get_current_metrics()

@router.get("/metrics/history", dependencies=[Depends(require_permission(Permission.VIEW_ANALYTICS))])
async def get_metrics_history(
    count: Optional[int] = Query(None, description="Dönülecek geçmiş sayısı")
):
    """
    Metrik geçmişini döndürür.
    
    Args:
        count: Dönülecek geçmiş sayısı (None ise tümü)
        
    Requires:
        - `view:analytics` permission
    """
    return monitoring_service.get_metrics_history(count)

@router.post("/metrics/register", dependencies=[Depends(require_permission(Permission.VIEW_ANALYTICS))])
async def register_custom_metric(
    name: str = Query(..., description="Metrik adı"),
    value: Any = Query(..., description="Metrik değeri")
):
    """
    Özel metrik kaydeder.
    
    Args:
        name: Metrik adı
        value: Metrik değeri
        
    Requires:
        - `view:analytics` permission
    """
    monitoring_service.register_custom_metric(name, value)
    return {"success": True, "message": f"Metric '{name}' registered"}

@router.get("/system", dependencies=[Depends(require_role(Role.ADMIN))])
async def get_system_info():
    """
    Detaylı sistem bilgilerini döndürür.
    
    Requires:
        - `admin` role
    """
    import psutil
    import platform
    import os
    import socket
    
    try:
        # Sistem bilgilerini topla
        cpu_cores = psutil.cpu_count(logical=False)
        cpu_threads = psutil.cpu_count(logical=True)
        
        # Bellek bilgileri
        memory = psutil.virtual_memory()
        
        # Diskler
        disks = []
        for part in psutil.disk_partitions(all=False):
            if os.name == 'nt' and ('cdrom' in part.opts or part.fstype == ''):
                # Windows'ta CD-ROM'u atla
                continue
                
            usage = psutil.disk_usage(part.mountpoint)
            disks.append({
                "device": part.device,
                "mountpoint": part.mountpoint,
                "fstype": part.fstype,
                "total_gb": usage.total / (1024**3),
                "used_gb": usage.used / (1024**3),
                "free_gb": usage.free / (1024**3),
                "percent_used": usage.percent
            })
        
        # Ağ bilgileri
        net_io = psutil.net_io_counters()
        net_if_addrs = psutil.net_if_addrs()
        
        # IP adres bilgisi
        ip_addresses = {
            "hostname": socket.gethostname(),
            "interfaces": {}
        }
        
        for interface, addrs in net_if_addrs.items():
            ip_addresses["interfaces"][interface] = []
            for addr in addrs:
                addr_info = {
                    "family": str(addr.family),
                    "address": addr.address
                }
                if addr.netmask:
                    addr_info["netmask"] = addr.netmask
                if addr.broadcast:
                    addr_info["broadcast"] = addr.broadcast
                    
                ip_addresses["interfaces"][interface].append(addr_info)
        
        # Çalışan işlemler
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'username', 'memory_percent', 'cpu_percent']):
            try:
                pinfo = proc.as_dict()
                processes.append({
                    "pid": pinfo['pid'],
                    "name": pinfo['name'],
                    "username": pinfo['username'],
                    "memory_percent": pinfo['memory_percent'],
                    "cpu_percent": pinfo['cpu_percent']
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
                
        # Top 10 bellek kullanan işlemler
        processes.sort(key=lambda x: x['memory_percent'], reverse=True)
        top_memory_processes = processes[:10]
        
        # Python bilgileri
        python_info = {
            "version": platform.python_version(),
            "implementation": platform.python_implementation(),
            "compiler": platform.python_compiler()
        }
        
        return {
            "system": {
                "hostname": socket.gethostname(),
                "platform": platform.platform(),
                "system": platform.system(),
                "release": platform.release(),
                "version": platform.version(),
                "architecture": platform.machine(),
                "processor": platform.processor(),
                "boot_time": psutil.boot_time()
            },
            "cpu": {
                "physical_cores": cpu_cores,
                "logical_cores": cpu_threads,
                "usage_percent": psutil.cpu_percent(interval=1),
                "load_avg": os.getloadavg() if hasattr(os, 'getloadavg') else None
            },
            "memory": {
                "total_gb": memory.total / (1024**3),
                "available_gb": memory.available / (1024**3),
                "used_gb": memory.used / (1024**3),
                "percent_used": memory.percent
            },
            "disks": disks,
            "network": {
                "bytes_sent": net_io.bytes_sent,
                "bytes_recv": net_io.bytes_recv,
                "packets_sent": net_io.packets_sent,
                "packets_recv": net_io.packets_recv,
                "ip_addresses": ip_addresses
            },
            "python": python_info,
            "top_memory_processes": top_memory_processes
        }
        
    except Exception as e:
        logger.error(f"Error getting system info: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting system info: {str(e)}"
        )

@router.post("/start", dependencies=[Depends(require_role(Role.ADMIN))])
async def start_monitoring():
    """
    Monitoring servisini başlatır.
    
    Requires:
        - `admin` role
    """
    try:
        await monitoring_service.start_monitoring()
        return {"success": True, "message": "Monitoring service started"}
    except Exception as e:
        logger.error(f"Error starting monitoring service: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error starting monitoring service: {str(e)}"
        )

@router.post("/stop", dependencies=[Depends(require_role(Role.ADMIN))])
async def stop_monitoring():
    """
    Monitoring servisini durdurur.
    
    Requires:
        - `admin` role
    """
    try:
        await monitoring_service.stop_monitoring()
        return {"success": True, "message": "Monitoring service stopped"}
    except Exception as e:
        logger.error(f"Error stopping monitoring service: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error stopping monitoring service: {str(e)}"
        )