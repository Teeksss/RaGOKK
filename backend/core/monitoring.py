    def get_metrics_history(self, count: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Metrik geçmişini döndürür
        
        Args:
            count: Dönülecek geçmiş sayısı (None ise tümü)
            
        Returns:
            List[Dict[str, Any]]: Metrik geçmişi
        """
        if count is None or count >= len(self.metrics_history):
            return self.metrics_history
            
        return self.metrics_history[-count:]
    
    def get_current_metrics(self) -> Dict[str, Any]:
        """
        Mevcut anlık metrikleri döndürür
        
        Returns:
            Dict[str, Any]: Mevcut metrikler
        """
        system_metrics = self._collect_system_metrics()
        custom_metrics = self._collect_custom_metrics()
        
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "metrics": {**system_metrics, **custom_metrics}
        }