import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { CloudRain } from 'lucide-react';

const Login = () => {
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');
    const navigate = useNavigate();

    const [isLogin, setIsLogin] = useState(true);
    const [message, setMessage] = useState('');

    const handleAuth = async (e) => {
        e.preventDefault();
        setError('');
        setMessage('');

        const endpoint = isLogin ? 'http://localhost:5000/login' : 'http://localhost:5000/signup';

        try {
            const res = await fetch(endpoint, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, password })
            });

            const data = await res.json();

            if (!res.ok) {
                throw new Error(data.error || 'Authentication failed');
            }

            if (isLogin) {
                localStorage.setItem('role', data.role);
                localStorage.setItem('username', username);
                // "has_llm_access" could be useful to store locally or check fresh on dashboard
                navigate('/dashboard');
            } else {
                setMessage('Account created! Please log in.');
                setIsLogin(true);
            }

        } catch (err) {
            setError(err.message);
        }
    };

    return (
        <div className="flex min-h-screen items-center justify-center p-4 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-slate-900 via-slate-950 to-black">
            <div className="w-full max-w-md space-y-8 rounded-2xl bg-white/5 p-8 backdrop-blur-lg border border-white/10 shadow-2xl">
                <div className="flex flex-col items-center justify-center text-center">
                    <div className="flex h-16 w-16 items-center justify-center rounded-full bg-blue-500/10 mb-4">
                        <CloudRain className="h-8 w-8 text-blue-400" />
                    </div>
                    <h2 className="text-3xl font-bold tracking-tight text-white">
                        {isLogin ? 'Welcome Back' : 'Create Account'}
                    </h2>
                    <p className="mt-2 text-sm text-slate-400">
                        {isLogin ? 'Sign in to access your dashboard' : 'Register to get started'}
                    </p>
                </div>

                <form className="mt-8 space-y-6" onSubmit={handleAuth}>
                    {error && (
                        <div className="p-3 text-sm text-red-400 bg-red-900/20 border border-red-900/50 rounded-lg text-center">
                            {error}
                        </div>
                    )}
                    {message && (
                        <div className="p-3 text-sm text-green-400 bg-green-900/20 border border-green-900/50 rounded-lg text-center">
                            {message}
                        </div>
                    )}

                    <div className="space-y-4">
                        <div>
                            <label htmlFor="username" className="text-sm font-medium text-slate-300">
                                Username
                            </label>
                            <input
                                id="username"
                                name="username"
                                type="text"
                                required
                                className="mt-1 block w-full rounded-lg bg-black/50 border border-white/10 px-3 py-2 text-white placeholder-slate-500 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition-all outline-none"
                                placeholder="Enter username"
                                value={username}
                                onChange={(e) => setUsername(e.target.value)}
                            />
                        </div>
                        <div>
                            <label htmlFor="password" className="text-sm font-medium text-slate-300">
                                Password
                            </label>
                            <input
                                id="password"
                                name="password"
                                type="password"
                                required
                                className="mt-1 block w-full rounded-lg bg-black/50 border border-white/10 px-3 py-2 text-white placeholder-slate-500 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition-all outline-none"
                                placeholder="••••••••"
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                            />
                        </div>
                    </div>

                    <button
                        type="submit"
                        className="group relative flex w-full justify-center rounded-lg bg-gradient-to-r from-blue-600 to-indigo-600 px-4 py-2.5 text-sm font-semibold text-white shadow-lg shadow-blue-500/20 hover:from-blue-500 hover:to-indigo-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 focus:ring-offset-slate-900 transition-all duration-200"
                    >
                        {isLogin ? 'Sign in' : 'Sign up'}
                    </button>

                    <div className="text-center">
                        <button
                            type="button"
                            onClick={() => {
                                setIsLogin(!isLogin);
                                setError('');
                                setMessage('');
                            }}
                            className="text-sm text-blue-400 hover:text-blue-300 transition-colors"
                        >
                            {isLogin ? "Don't have an account fucker5?" : 'Already have an account? Sign in'}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
};

export default Login;
