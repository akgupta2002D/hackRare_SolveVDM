import { useState } from "react";
import { useNavigate } from "react-router-dom";

export default function VirtuousLeftNav() {
  const navigate = useNavigate();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const go = (path) => {
    navigate(path);
    setMobileMenuOpen(false);
  };

return (
    <header className="virtuousLeftNav noFloatersEffect" data-interactive="true">
        <div className="virtuousLeftNavInner">
            <div className="virtuousLeftNavBrand">VIRTUOUS</div>

            <nav className="virtuousLeftNavActions">
                <button
                    className=" virtuousNavBtnEmergency  "
                    onClick={() => go("/emergency")}
                >
                    🚨 Seeing New Floaters
                </button>
                <button
                    className="virtuousNavBtn virtuousNavBtnMenu"
                    onClick={() => setMobileMenuOpen(true)}
                    aria-label="Open menu"
                >
                    ☰ Menu
                </button>

                <button
                    className="virtuousNavBtn virtuousNavBtnDesktop"
                    onClick={() => go("/future")}
                >
                    🛠️ Future Direction
                </button>
                <button
                    className="virtuousNavBtn virtuousNavBtnDesktop"
                    onClick={() => go("/resources")}
                >
                    Resources
                </button>
                <button
                    className="virtuousNavBtn virtuousNavBtnDesktop virtuousNavBtnPrimary"
                    onClick={() => go("/signin")}
                >
                   🛠️ Sign In 
                </button>
            </nav>
        </div>
        <div
            className={`virtuousMobileMenuBackdrop ${mobileMenuOpen ? "isOpen" : ""}`}
            onClick={() => setMobileMenuOpen(false)}
            aria-hidden={!mobileMenuOpen}
        />
        <aside className={`virtuousMobileDrawer ${mobileMenuOpen ? "isOpen" : ""}`}>
            <button
                className="virtuousNavBtn virtuousMobileDrawerClose"
                onClick={() => setMobileMenuOpen(false)}
                aria-label="Close menu"
            >
                ✕
            </button>
            <button className="virtuousNavBtn" onClick={() => go("/future")}>
                🛠️ Future Direction
            </button>
            <button className="virtuousNavBtn" onClick={() => go("/resources")}>
                Resources
            </button>
            <button className="virtuousNavBtn virtuousNavBtnPrimary" onClick={() => go("/signin")}>
               🛠️ Sign In
            </button>
            <button className="blue_border virtuousBtn" onClick={() => go("/emulator")}>
                Patient: Emulator
            </button>
            <button className="red_border virtuousBtn" onClick={() => go("/clinical")}>
                Clinicians: Info and Data
            </button>
        </aside>
    </header>
);
}