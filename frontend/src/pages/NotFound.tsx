import { Link } from "react-router-dom";

export function NotFound() {
  return (
    <div className="page">
      <h1 className="page-title">Page not found</h1>
      <p className="lede">This address doesn't match a Greenr workspace.</p>
      <p style={{ marginTop: 16 }}><Link className="btn btn-primary" to="/customers">Go to customers</Link></p>
    </div>
  );
}
