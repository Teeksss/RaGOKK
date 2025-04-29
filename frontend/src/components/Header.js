// Last reviewed: 2025-04-29 10:51:12 UTC (User: TeeksssPrioritizationTest.js)
// Admin menüsüne PrioritizationTest için ek link ekliyoruz:

{adminMenuOpen && (
  <ul className="admin-dropdown">
    <li>
      <Link 
        to="/models" 
        className={isActive('/models')}
        onClick={closeMenu}
      >
        Model Yönetimi
      </Link>
    </li>
    <li>
      <Link 
        to="/api-keys/monitor" 
        className={isActive('/api-keys/monitor')}
        onClick={closeMenu}
      >
        API İzleme
      </Link>
    </li>
    <li>
      <Link 
        to="/priority-test" 
        className={isActive('/priority-test')}
        onClick={closeMenu}
      >
        Önceliklendirme Testi
      </Link>
    </li>
    <li>
      <Link 
        to="/settings/admin" 
        className={isActive('/settings/admin')}
        onClick={closeMenu}
      >
        Admin Ayarları
      </Link>
    </li>
  </ul>
)}