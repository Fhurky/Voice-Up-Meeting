import { useAuth } from "@/contexts/AuthContext";
import { config } from "@/lib/config";

export default function HomePage() {
  const { user, logout } = useAuth();
  return (
    <main className="home">
      <header>
        <div>
          <div className="eyebrow">{config.primaryDomain}</div>
          <h1>{config.productName}</h1>
        </div>
        <button onClick={logout}>Sign out</button>
      </header>
      <section className="hero">
        <p>{config.projectIntent}</p>
        <dl>
          <div>
            <dt>Actor</dt>
            <dd>{user?.username}</dd>
          </div>
          <div>
            <dt>Tenant</dt>
            <dd>{user?.tenant_id}</dd>
          </div>
          <div>
            <dt>Authority</dt>
            <dd>
              {user?.is_super_admin ? "super_admin" : user?.roles?.join(", ")}
            </dd>
          </div>
        </dl>
      </section>
      <section className="empty-state">
        <h2>Ready for the first accepted domain PRD</h2>
        <p>No placeholder business resource has been generated.</p>
      </section>
    </main>
  );
}
