'use client';
import { useState } from 'react';
import RepositoryInputForm from '@/components/RepositoryInputForm';
import { useRouter } from 'next/navigation';

export default function Home() {
  const router = useRouter();
  const [isScanning, setIsScanning] = useState(false);

  const handleScanStarted = (id: number) => {
    setIsScanning(true);
    router.push(`/scan/${id}`);
  };

  return (
    <div className="min-h-screen bg-black text-white p-8">
      <main className="max-w-4xl mx-auto space-y-12 mt-16">
        <div className="text-center space-y-4">
          <h1 className="text-5xl font-extrabold tracking-tight bg-gradient-to-r from-blue-400 to-emerald-400 text-transparent bg-clip-text drop-shadow-sm">
            SynodOSS
          </h1>
          <p className="text-xl text-neutral-400 font-light">
            Repository Intelligence & Divergence Analysis
          </p>
        </div>

        <div className="bg-neutral-900/50 p-8 rounded-2xl border border-neutral-800 shadow-2xl backdrop-blur-sm">
           <RepositoryInputForm onScanStarted={handleScanStarted} />
        </div>
      </main>
    </div>
  );
}
