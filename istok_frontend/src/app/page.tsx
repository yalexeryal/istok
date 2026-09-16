'use client';

import { useState } from 'react';

export default function Home() {
  const [email, setEmail] = useState('yalexer@istok.family');
  const [password, setPassword] = useState('yalexer123');
  const [result, setResult] = useState<string>('Введите данные и нажмите "Войти"');
  const [isLoading, setIsLoading] = useState(false);

    const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setResult('Отправка запроса...');

    try {
      // Отправляем данные в формате JSON
      const response = await fetch('http://127.0.0.1:8000/auth/login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json', // <-- Важно: указываем JSON
        },
        body: JSON.stringify({
          username: email,
          password: password,
        }),
      });

      const data = await response.json();

      if (response.ok) {
        setResult(`✅ Успех! ${data.message}`);
      } else {
        // Если есть детальная ошибка от Pydantic или наша
        const errorMsg = data.detail
          ? (Array.isArray(data.detail) ? data.detail[0].msg : data.detail)
          : 'Неизвестная ошибка';
        setResult(`❌ Ошибка: ${errorMsg}`);
      }
    } catch (err: any) {
      setResult(`❌ Ошибка сети: ${err.message}`);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-24 bg-gray-50">
      <h1 className="text-4xl font-bold text-gray-900 mb-8">🌳 Исток</h1>

      <form onSubmit={handleLogin} className="w-full max-w-md p-6 bg-white rounded-xl shadow-lg border border-gray-200 space-y-4">
        <h2 className="text-xl font-semibold text-gray-700 text-center mb-4">Вход в систему</h2>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
          <input
            type="text"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
            required
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Пароль</label>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
            required
          />
        </div>

        <button
          type="submit"
          disabled={isLoading}
          className="w-full py-2 px-4 bg-indigo-600 text-white font-medium rounded-md hover:bg-indigo-700 disabled:opacity-50 transition-colors"
        >
          {isLoading ? 'Вход...' : 'Войти'}
        </button>

        <div className="mt-4 p-3 bg-gray-50 rounded text-sm font-mono text-center break-words">
          {result}
        </div>
      </form>
    </main>
  );
}