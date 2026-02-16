import { NavLink, useLocation } from "react-router-dom";
import { useEffect, useState } from "react";

const Navbar = () => {
  const location = useLocation();
  const [viewportWidth, setViewportWidth] = useState(() =>
    typeof window !== "undefined" ? window.innerWidth : 1024
  );
  const [menuOpen, setMenuOpen] = useState(false);
  const isMobile = viewportWidth < 768;

  useEffect(() => {
    if (typeof window === "undefined") return undefined;
    const onResize = () => setViewportWidth(window.innerWidth);
    window.addEventListener("resize", onResize);
    return () => window.removeEventListener("resize", onResize);
  }, []);

  useEffect(() => {
    setMenuOpen(false);
  }, [location.pathname, isMobile]);

  const links = [
    { to: "/offense", label: "Offense" },
    { to: "/defense", label: "Defense" },
    { to: "/trends", label: "Trends" },
    { to: "/odds", label: "Odds" },
    { to: "/player-trends", label: "Player Trends" },
    { to: "/player-insights", label: "Player Insights" },
    { to: "/narrative-dashboard", label: "Narrative Dashboard" },
  ];

  const linkStyle = {
    color: "#ccc",
    textDecoration: "none",
    padding: isMobile ? "10px 12px" : "10px 16px",
    borderRadius: "8px",
    transition: "all 0.2s ease-in-out",
    whiteSpace: "nowrap",
    flex: isMobile ? "1 1 auto" : "0 0 auto",
    textAlign: isMobile ? "left" : "center",
  };

  const activeStyle = {
    backgroundColor: "#333",
    color: "#fff",
  };

  const renderLinks = () =>
    links.map((link) => (
      <NavLink
        key={link.to}
        to={link.to}
        style={({ isActive }) =>
          isActive ? { ...linkStyle, ...activeStyle } : linkStyle
        }
      >
        {link.label}
      </NavLink>
    ));

  if (isMobile) {
    return (
      <nav
        style={{
          backgroundColor: "#111",
          borderBottom: "1px solid #222",
          position: "sticky",
          top: 0,
          zIndex: 1000,
        }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            padding: "10px 12px",
          }}
        >
          <div style={{ color: "#e5e7eb", fontWeight: 700, fontSize: 14 }}>Navigation</div>
          <button
            onClick={() => setMenuOpen((v) => !v)}
            style={{
              border: "1px solid #334155",
              background: "#1f2937",
              color: "#fff",
              borderRadius: 8,
              padding: "6px 10px",
              fontWeight: 700,
              cursor: "pointer",
            }}
            aria-label={menuOpen ? "Close menu" : "Open menu"}
            title={menuOpen ? "Close menu" : "Open menu"}
          >
            {menuOpen ? "Close" : "Menu"}
          </button>
        </div>

        {menuOpen && (
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              gap: 6,
              padding: "0 10px 10px 10px",
              background: "#0f1117",
              borderTop: "1px solid #1f2937",
            }}
          >
            {renderLinks()}
          </div>
        )}
      </nav>
    );
  }

  return (
    <nav
      style={{
        display: "flex",
        justifyContent: "center",
        alignItems: "center",
        gap: "10px",
        backgroundColor: "#111",
        padding: "12px",
        borderBottom: "1px solid #222",
        position: "sticky",
        top: 0,
        zIndex: 1000,
      }}
    >
      {renderLinks()}
    </nav>
  );
};

export default Navbar;
