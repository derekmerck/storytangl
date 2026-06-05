// wp-app.jsx — assemble the World Profiles design study.

function WorldProfilesDoc() {
  return (
    <div className="paper">
      <TopBanner />
      <div className="page">
        <Lede />
        <MatrixSection />
        <HandshakeSection />
        <ContractSection />
        <ProofSection />

        <div className="sec-head" style={{ marginTop: 46 }}>
          <span className="idx">§4–6</span>
          <h2>Three worlds, in their signature shell</h2>
          <span className="sub">real fixtures, full costume</span>
        </div>
        <p className="prose" style={{ maxWidth: 880 }}>
          The proof strip showed one structural turn re-skinned. Here each world wears
          its own real fixture in the shell its loop wants — carwars in the garage
          dossier, the booth mid-inspection, the court mid-week. Same widgets, same
          rail grammar, same gates. Only the world changed.
        </p>

        <CarwarsDive />
        <CredentialsDive />
        <RegentDive />
        <RenderAxisSection />
        <LogoSection />
        <FloorSection />
      </div>
    </div>
  );
}

ReactDOM.createRoot(document.getElementById("root")).render(<WorldProfilesDoc />);
