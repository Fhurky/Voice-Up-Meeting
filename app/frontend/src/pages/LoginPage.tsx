import {useEffect, useState, type FormEvent} from 'react';
import {Navigate, useNavigate} from 'react-router';
import {useAuth} from '@/contexts/AuthContext';
import {useIntl} from '@/contexts/IntlContext';
import {ApiError} from '@/lib/apiClient';
import {AuthService} from '@/services/auth';
import {Icon} from '@/components/ui/Icon';
import {VoiceWave} from '@/components/ui/VoiceWave';

export default function LoginPage() {
  const {user, login, loginAsAdmin} = useAuth();
  const {locale, setLocale, t} = useIntl();
  const navigate = useNavigate();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState<'password' | 'admin' | null>(null);
  const [localAdminEnabled, setLocalAdminEnabled] = useState(false);
  const title = t('login.title');
  useEffect(() => { document.title = `${title} · VoiceUp`; }, [title]);
  useEffect(() => {
    let active = true;
    void AuthService.options().then((options) => {
      if (active) setLocalAdminEnabled(options.local_admin_login_enabled === true);
    }).catch(() => { /* Password sign-in remains available if discovery fails. */ });
    return () => { active = false; };
  }, []);
  if (user) return <Navigate to="/" replace />;

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (busy) return;
    setBusy('password');
    setError('');
    try {
      await login(username, password);
      navigate('/', {replace: true});
    } catch (caught) {
      setError(caught instanceof ApiError && caught.status === 401 ? 'login.error' : 'login.unavailable');
    } finally {
      setBusy(null);
    }
  }

  async function submitAdmin() {
    if (busy || !localAdminEnabled) return;
    setBusy('admin');
    setError('');
    try {
      await loginAsAdmin();
      navigate('/', {replace: true});
    } catch (caught) {
      setError(caught instanceof ApiError && caught.status === 404
        ? 'login.adminDisabled'
        : caught instanceof ApiError && caught.code === 'local_admin_unavailable'
          ? 'login.adminUnavailable' : 'login.unavailable');
    } finally {
      setBusy(null);
    }
  }

  return (
    <main className="login-shell">
      <section className="login-story" aria-labelledby="login-story-title">
        <div className="brand-lockup"><span className="brand-mark"><Icon name="audio" size={26} /></span><span>VoiceUp</span></div>
        <div className="login-story-copy">
          <div className="eyebrow">{t('login.storyEyebrow')}</div>
          <h2 id="login-story-title">{t('login.storyTitle')}</h2>
          <p>{t('login.storyBody')}</p>
          <VoiceWave />
        </div>
        <ol className="login-story-steps">
          {(['login.storyUpload', 'login.storyIdentify', 'login.storyRemember'] as const).map((key, index) => <li key={key}><span aria-hidden="true">{String(index + 1).padStart(2, '0')}</span>{t(key)}</li>)}
        </ol>
      </section>
      <section className="login-form-side" aria-labelledby="login-heading">
        <div className="login-toolbar"><button className="language button-quiet" type="button" onClick={() => setLocale(locale === 'en' ? 'tr' : 'en')}>
          <Icon name="globe" size={16} />{t('common.otherLanguage')}
        </button></div>
        <div className="login-card">
          <div className="eyebrow">{t('login.title')}</div>
          <h1 id="login-heading">{t('login.welcome')}</h1>
          <p>{t('login.subtitle')}</p>
          <form onSubmit={submit}>
            <label htmlFor="username">{t('login.username')}</label>
            <input id="username" autoComplete="username" value={username} onChange={(e) => setUsername(e.target.value)} />
            <label htmlFor="password">{t('login.password')}</label>
            <input id="password" type="password" autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} />
            {error && <div className="error-message" role="alert">{t(error)}</div>}
            <button type="submit" disabled={busy !== null}>{busy === 'password' ? t('login.busy') : t('login.submit')}<Icon name="arrow-right" size={18} /></button>
            {localAdminEnabled && <div className="login-admin-block">
              <div className="login-divider">{t('login.divider')}</div>
              <button className="button-secondary" type="button" disabled={busy !== null} onClick={() => { void submitAdmin(); }}>
                <Icon name="shield" size={18} />{busy === 'admin' ? t('login.busy') : t('login.admin')}
              </button>
              <p className="field-hint">{t('login.adminHint')}</p>
            </div>}
          </form>
        </div>
      </section>
    </main>
  );
}
