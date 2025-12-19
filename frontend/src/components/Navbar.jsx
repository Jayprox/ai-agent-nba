import { NavLink } from "react-router-dom";

const Navbar = () => {
  const linkStyle = {
    color: "#ccc",
    textDecoration: "none",
    padding: "10px 16px",
    borderRadius: "8px",
    transition: "all 0.2s ease-in-out",
  };

  const activeStyle = {
    backgroundColor: "#333",
    color: "#fff",
  };

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
      <NavLink
        to="/offense"
        style={({ isActive }) =>
          isActive ? { ...linkStyle, ...activeStyle } : linkStyle
        }
      >
        Offense
      </NavLink>

      <NavLink
        to="/defense"
        style={({ isActive }) =>
          isActive ? { ...linkStyle, ...activeStyle } : linkStyle
        }
      >
        Defense
      </NavLink>

      <NavLink
        to="/trends"
        style={({ isActive }) =>
          isActive ? { ...linkStyle, ...activeStyle } : linkStyle
        }
      >
        Trends
      </NavLink>

      <NavLink
        to="/odds"
        style={({ isActive }) =>
          isActive ? { ...linkStyle, ...activeStyle } : linkStyle
        }
      >
        Odds
      </NavLink>

      <NavLink
        to="/player-trends"
        style={({ isActive }) =>
          isActive ? { ...linkStyle, ...activeStyle } : linkStyle
        }
      >
        Player Trends
      </NavLink>

      <NavLink
        to="/player-insights"
        style={({ isActive }) =>
          isActive ? { ...linkStyle, ...activeStyle } : linkStyle
        }
      >
        Player Insights
      </NavLink>
      <NavLink
        to="/narrative-dashboard"
        style={({ isActive }) =>
          isActive ? { ...linkStyle, ...activeStyle } : linkStyle
        }
      >
        Narrative Dashboard
      </NavLink>
    </nav>
  );
};

export default Navbar;
