import { useNavigate } from "react-router-dom";

export default function VirtuousLeftNav() {
  const navigate = useNavigate();

return (
    <header className="virtuousLeftNav noFloatersEffect" data-interactive="true">
        <div className="virtuousLeftNavInner">
            <div className="virtuousLeftNavBrand">VIRTUOUS</div>

            <nav className="virtuousLeftNavActions">
                <button
                    className=" virtuousNavBtnEmergency  "
                    onClick={() => navigate("/emergency")}
                >
                    🚨 Seeing New Floaters
                </button>

                <button
                    className="virtuousNavBtn virtuousNavBtn"
                    onClick={() => navigate("/future")}
                >
                    🛠️ Future Direction
                </button>
                <button
                    className="virtuousNavBtn virtuousNavBtn"
                    onClick={() => navigate("/resources")}
                >
                    Resources
                </button>
                <button
                    className="virtuousNavBtn virtuousNavBtn virtuousNavBtnPrimary"
                    onClick={() => navigate("/signin")}
                >
                   🛠️ Sign In 
                </button>
            </nav>
        </div>
    </header>
);
}