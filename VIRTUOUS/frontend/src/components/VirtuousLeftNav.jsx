import { useNavigate } from "react-router-dom";

export default function VirtuousLeftNav() {
  const navigate = useNavigate();

  return (
    <header className="virtuousLeftNav noFloatersEffect" data-interactive="true">
      <div className="virtuousLeftNavInner">
        <div className="virtuousLeftNavBrand">VIRTUOUS</div>

        <nav className="virtuousLeftNavActions">
          <button
            className="virtuousBtn virtuousNavBtn virtuousNavBtnEmergency"
            onClick={() => navigate("/emergency")}
          >
            ☣ Emergency
          </button>

          <button className="virtuousBtn virtuousNavBtn">About Us</button>
          <button className="virtuousBtn virtuousNavBtn">Resources</button>
          <button className="virtuousBtn virtuousNavBtn">Contact</button>
          <button className="virtuousBtn virtuousNavBtn">Pricing</button>
          <button
            className="virtuousBtn virtuousNavBtn virtuousNavBtnPrimary"
            onClick={() => navigate("/signin")}
          >
            Sign In
          </button>
        </nav>
      </div>
    </header>
  );
}