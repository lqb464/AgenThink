"use client";

import React, { useState } from "react";
import { BrainCircuit, Loader2 } from "lucide-react";
import { loginUser, registerUser } from "../lib/api";
import { setAuthSession, AuthUser } from "../lib/auth";

interface AuthScreenProps {
  onAuthenticated: (user: AuthUser) => void;
  language?: "vi" | "en";
}

export function AuthScreen({ onAuthenticated, language = "vi" }: AuthScreenProps) {
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const t =
    language === "en"
      ? {
          title: "Sign in to AgenThink",
          subtitle: "Multi-user hybrid agent — your chats & docs stay private",
          login: "Sign in",
          register: "Create account",
          email: "Email",
          password: "Password",
          switchLogin: "Already have an account? Sign in",
          switchReg: "New here? Create an account",
          hint: "Demo seed (compose): demo@local / change-me",
        }
      : {
          title: "Đăng nhập AgenThink",
          subtitle: "Agent hybrid đa người dùng — chat & tài liệu được cô lập",
          login: "Đăng nhập",
          register: "Tạo tài khoản",
          email: "Email",
          password: "Mật khẩu",
          switchLogin: "Đã có tài khoản? Đăng nhập",
          switchReg: "Chưa có tài khoản? Đăng ký",
          hint: "Demo (compose): demo@local / change-me",
        };

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const data =
        mode === "login"
          ? await loginUser(email.trim(), password)
          : await registerUser(email.trim(), password);
      setAuthSession(data.access_token, data.refresh_token, data.user);
      onAuthenticated(data.user);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Auth failed";
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#060a12] px-4 relative overflow-hidden">
      <div className="absolute top-1/4 left-1/3 w-96 h-96 bg-emerald-500/10 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute bottom-1/4 right-1/4 w-80 h-80 bg-[#0095ff]/10 rounded-full blur-3xl pointer-events-none" />

      <div className="w-full max-w-md relative z-10">
        <div className="flex flex-col items-center mb-8 gap-3">
          <div className="w-14 h-14 rounded-2xl bg-gradient-to-tr from-emerald-500 via-teal-500 to-cyan-500 flex items-center justify-center shadow-lg shadow-emerald-500/25">
            <BrainCircuit className="w-7 h-7 text-white" />
          </div>
          <h1 className="text-2xl font-extrabold tracking-tight bg-gradient-to-r from-emerald-300 via-teal-200 to-cyan-300 bg-clip-text text-transparent">
            AgenThink
          </h1>
          <p className="text-sm text-slate-400 text-center">{t.subtitle}</p>
        </div>

        <form
          onSubmit={submit}
          className="rounded-2xl border border-slate-800/80 bg-slate-950/80 backdrop-blur-xl p-6 space-y-4 shadow-xl"
        >
          <h2 className="text-lg font-semibold text-slate-100">
            {mode === "login" ? t.login : t.register}
          </h2>

          <label className="block space-y-1.5">
            <span className="text-xs text-slate-400 uppercase tracking-wider">{t.email}</span>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full rounded-xl bg-slate-900 border border-slate-700 px-3 py-2.5 text-sm text-slate-100 focus:outline-none focus:border-emerald-500/60"
              placeholder="you@example.com"
              autoComplete="email"
            />
          </label>

          <label className="block space-y-1.5">
            <span className="text-xs text-slate-400 uppercase tracking-wider">{t.password}</span>
            <input
              type="password"
              required
              minLength={6}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full rounded-xl bg-slate-900 border border-slate-700 px-3 py-2.5 text-sm text-slate-100 focus:outline-none focus:border-emerald-500/60"
              placeholder="••••••••"
              autoComplete={mode === "login" ? "current-password" : "new-password"}
            />
          </label>

          {error && (
            <p className="text-xs text-rose-400 bg-rose-500/10 border border-rose-500/20 rounded-lg px-3 py-2">
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full flex items-center justify-center gap-2 py-2.5 rounded-xl font-medium text-sm bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white disabled:opacity-60 transition-all"
          >
            {loading && <Loader2 className="w-4 h-4 animate-spin" />}
            {mode === "login" ? t.login : t.register}
          </button>

          <button
            type="button"
            onClick={() => {
              setMode(mode === "login" ? "register" : "login");
              setError("");
            }}
            className="w-full text-xs text-slate-400 hover:text-emerald-300 transition-colors"
          >
            {mode === "login" ? t.switchReg : t.switchLogin}
          </button>
        </form>

        <p className="mt-4 text-center text-[11px] text-slate-600">{t.hint}</p>
      </div>
    </div>
  );
}
