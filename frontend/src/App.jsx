import React, { useState, useEffect } from 'react';
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { Spider, Globe, ShoppingCart, FileText, Play, Trash2, RefreshCw, CheckCircle, XCircle, Clock, Database } from 'lucide-react';

const API_URL = 'http://localhost:8002';

function StatCard({ icon: Icon, label, value, color }) {
  return (
    <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
      <div className="flex items-center gap-4">
        <div className={`p-3 rounded-lg ${color}`}>
          <Icon className="w-6 h-6 text-white" />
        </div>
        <div>
          <p className="text-sm text-gray-500">{label}</p>
          <p className="text-2xl font-bold text-gray-900">{value}</p>
        </div>
      </div>
    </div>
  );
}

function JobRow({ job, onDelete, onRefresh }) {
  const statusColors = {
    completado: 'bg-green-100 text-green-800',
    error: 'bg-red-100 text-red-800',
    ejecutando: 'bg-blue-100 text-blue-800',
    pendiente: 'bg-yellow-100 text-yellow-800'
  };

  const typeIcons = {
    noticias: Globe,
    ecommerce: ShoppingCart,
    generico: FileText
  };

  const TypeIcon = typeIcons[job.tipo] || Globe;

  return (
    <tr className="border-b border-gray-100 hover:bg-gray-50">
      <td className="py-4 px-4">
        <div className="flex items-center gap-3">
          <TypeIcon className="w-5 h-5 text-indigo-600" />
          <span className="font-medium">{job.tipo}</span>
        </div>
      </td>
      <td className="py-4 px-4">
        <span className="text-sm text-gray-600 truncate max-w-xs block">{job.url}</span>
      </td>
      <td className="py-4 px-4">
        <span className={`px-3 py-1 rounded-full text-xs font-medium ${statusColors[job.estado]}`}>
          {job.estado}
        </span>
      </td>
      <td className="py-4 px-4">
        {job.estado === 'ejecutando' ? (
          <div className="flex items-center gap-2">
            <div className="w-24 h-2 bg-gray-200 rounded-full overflow-hidden">
              <div 
                className="h-full bg-indigo-600 rounded-full transition-all"
                style={{ width: `${job.progreso}%` }}
              />
            </div>
            <span className="text-sm text-gray-600">{job.progreso}%</span>
          </div>
        ) : (
          <span className="text-sm text-gray-600">{job.resultados_count} resultados</span>
        )}
      </td>
      <td className="py-4 px-4 text-sm text-gray-500">
        {job.fecha_inicio ? new Date(job.fecha_inicio).toLocaleString() : '-'}
      </td>
      <td className="py-4 px-4">
        <button
          onClick={() => onDelete(job.id)}
          className="p-2 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition"
        >
          <Trash2 className="w-4 h-4" />
        </button>
      </td>
    </tr>
  );
}

export default function App() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [jobs, setJobs] = useState([]);
  const [stats, setStats] = useState({ total_jobs: 0, jobs_completados: 0, jobs_activos: 0, jobs_errores: 0, total_resultados: 0 });
  const [graficoData, setGraficoData] = useState([]);
  const [url, setUrl] = useState('');
  const [tipo, setTipo] = useState('noticias');
  const [maxItems, setMaxItems] = useState(10);
  const [exportFormat, setExportFormat] = useState('');
  const [loading, setLoading] = useState(false);
  const [selectedJob, setSelectedJob] = useState(null);

  const fetchJobs = async () => {
    try {
      const res = await fetch(`${API_URL}/api/scraping/trabajos`);
      const data = await res.json();
      setJobs(data);
    } catch (err) {
      console.error('Error fetching jobs:', err);
    }
  };

  const fetchStats = async () => {
    try {
      const res = await fetch(`${API_URL}/api/estadisticas`);
      const data = await res.json();
      setStats(data);
    } catch (err) {
      console.error('Error fetching stats:', err);
    }
  };

  const fetchGrafico = async () => {
    try {
      const res = await fetch(`${API_URL}/api/scraping/grafico-trabajos`);
      const data = await res.json();
      setGraficoData(data);
    } catch (err) {
      console.error('Error fetching chart:', err);
    }
  };

  const fetchJobDetail = async (jobId) => {
    try {
      const res = await fetch(`${API_URL}/api/scraping/trabajos/${jobId}`);
      const data = await res.json();
      setSelectedJob(data);
    } catch (err) {
      console.error('Error fetching job detail:', err);
    }
  };

  useEffect(() => {
    fetchJobs();
    fetchStats();
    fetchGrafico();
    const interval = setInterval(() => {
      fetchJobs();
      fetchStats();
    }, 5000);
    return () => clearInterval(interval);
  }, []);

  const ejecutarScraping = async () => {
    if (!url) return;
    setLoading(true);
    try {
      await fetch(`${API_URL}/api/scraping/ejecutar`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url, tipo, max_items: maxItems, export_format: exportFormat || null })
      });
      setUrl('');
      fetchJobs();
      fetchStats();
      fetchGrafico();
    } catch (err) {
      console.error('Error executing scraping:', err);
    }
    setLoading(false);
  };

  const eliminarTrabajo = async (jobId) => {
    try {
      await fetch(`${API_URL}/api/scraping/trabajos/${jobId}`, { method: 'DELETE' });
      fetchJobs();
      fetchStats();
      if (selectedJob?.id === jobId) setSelectedJob(null);
    } catch (err) {
      console.error('Error deleting job:', err);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-indigo-600 rounded-lg">
                <Spider className="w-6 h-6 text-white" />
              </div>
              <h1 className="text-xl font-bold text-gray-900">Web Scraper Pro</h1>
            </div>
            <div className="flex items-center gap-4">
              <span className="text-sm text-gray-500">API: {stats.jobs_activos > 0 ? 'Activo' : 'Inactivo'}</span>
              <button onClick={() => { fetchJobs(); fetchStats(); fetchGrafico(); }} className="p-2 hover:bg-gray-100 rounded-lg">
                <RefreshCw className="w-5 h-5 text-gray-600" />
              </button>
            </div>
          </div>
        </div>
      </header>

      <nav className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-6">
          <div className="flex gap-8">
            {['dashboard', 'trabajos', 'nuevo'].map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`py-4 px-2 border-b-2 text-sm font-medium transition ${
                  activeTab === tab
                    ? 'border-indigo-600 text-indigo-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700'
                }`}
              >
                {tab === 'dashboard' ? 'Dashboard' : tab === 'trabajos' ? 'Trabajos' : 'Nuevo Scraping'}
              </button>
            ))}
          </div>
        </div>
      </nav>

      <main className="max-w-7xl mx-auto px-6 py-8">
        {activeTab === 'dashboard' && (
          <div className="space-y-8">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
              <StatCard icon={Database} label="Total Jobs" value={stats.total_jobs} color="bg-indigo-600" />
              <StatCard icon={CheckCircle} label="Completados" value={stats.jobs_completados} color="bg-green-600" />
              <StatCard icon={Clock} label="En Proceso" value={stats.jobs_activos} color="bg-blue-600" />
              <StatCard icon={XCircle} label="Errores" value={stats.jobs_errores} color="bg-red-600" />
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
                <h3 className="text-lg font-semibold mb-4">Trabajos por Día</h3>
                <ResponsiveContainer width="100%" height={250}>
                  <BarChart data={graficoData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="fecha" />
                    <YAxis />
                    <Tooltip />
                    <Bar dataKey="trabajos" fill="#6366f1" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>

              <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
                <h3 className="text-lg font-semibold mb-4">Últimos Trabajos</h3>
                <div className="space-y-3">
                  {jobs.slice(0, 5).map((job) => (
                    <div key={job.id} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                      <div className="flex items-center gap-3">
                        {job.estado === 'completado' && <CheckCircle className="w-5 h-5 text-green-600" />}
                        {job.estado === 'error' && <XCircle className="w-5 h-5 text-red-600" />}
                        {job.estado === 'ejecutando' && <Clock className="w-5 h-5 text-blue-600" />}
                        <div>
                          <p className="font-medium text-sm">{job.tipo}</p>
                          <p className="text-xs text-gray-500 truncate max-w-xs">{job.url}</p>
                        </div>
                      </div>
                      <span className="text-xs text-gray-500">{job.resultados_count} resultados</span>
                    </div>
                  ))}
                  {jobs.length === 0 && <p className="text-gray-500 text-center py-8">No hay trabajos aún</p>}
                </div>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'trabajos' && (
          <div className="bg-white rounded-xl shadow-sm border border-gray-100">
            <div className="p-6 border-b border-gray-100">
              <h2 className="text-lg font-semibold">Trabajos de Scraping</h2>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="py-3 px-4 text-left text-xs font-medium text-gray-500 uppercase">Tipo</th>
                    <th className="py-3 px-4 text-left text-xs font-medium text-gray-500 uppercase">URL</th>
                    <th className="py-3 px-4 text-left text-xs font-medium text-gray-500 uppercase">Estado</th>
                    <th className="py-3 px-4 text-left text-xs font-medium text-gray-500 uppercase">Progreso</th>
                    <th className="py-3 px-4 text-left text-xs font-medium text-gray-500 uppercase">Fecha</th>
                    <th className="py-3 px-4 text-left text-xs font-medium text-gray-500 uppercase">Acciones</th>
                  </tr>
                </thead>
                <tbody>
                  {jobs.map((job) => (
                    <JobRow key={job.id} job={job} onDelete={eliminarTrabajo} onRefresh={fetchJobDetail} />
                  ))}
                  {jobs.length === 0 && (
                    <tr>
                      <td colSpan="6" className="py-12 text-center text-gray-500">No hay trabajos registrados</td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {activeTab === 'nuevo' && (
          <div className="max-w-2xl mx-auto">
            <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
              <h2 className="text-lg font-semibold mb-6">Nuevo Trabajo de Scraping</h2>
              
              <div className="space-y-6">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">URL</label>
                  <input
                    type="url"
                    value={url}
                    onChange={(e) => setUrl(e.target.value)}
                    placeholder="https://ejemplo.com"
                    className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Tipo de Scraping</label>
                  <div className="grid grid-cols-3 gap-4">
                    {[
                      { value: 'noticias', label: 'Noticias', icon: Globe },
                      { value: 'ecommerce', label: 'E-commerce', icon: ShoppingCart },
                      { value: 'generico', label: 'Genérico', icon: FileText }
                    ].map((opt) => (
                      <button
                        key={opt.value}
                        onClick={() => setTipo(opt.value)}
                        className={`p-4 rounded-lg border-2 flex flex-col items-center gap-2 transition ${
                          tipo === opt.value
                            ? 'border-indigo-600 bg-indigo-50 text-indigo-600'
                            : 'border-gray-200 hover:border-gray-300'
                        }`}
                      >
                        <opt.icon className="w-6 h-6" />
                        <span className="text-sm font-medium">{opt.label}</span>
                      </button>
                    ))}
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Máximo de Items: {maxItems}</label>
                  <input
                    type="range"
                    min="1"
                    max="100"
                    value={maxItems}
                    onChange={(e) => setMaxItems(parseInt(e.target.value))}
                    className="w-full"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Formato de Exportación</label>
                  <select
                    value={exportFormat}
                    onChange={(e) => setExportFormat(e.target.value)}
                    className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
                  >
                    <option value="">Sin exportar</option>
                    <option value="json">JSON</option>
                    <option value="csv">CSV</option>
                    <option value="excel">Excel</option>
                  </select>
                </div>

                <button
                  onClick={ejecutarScraping}
                  disabled={!url || loading}
                  className="w-full py-3 px-4 bg-indigo-600 text-white rounded-lg font-medium hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                >
                  {loading ? (
                    <>
                      <RefreshCw className="w-5 h-5 animate-spin" />
                      Ejecutando...
                    </>
                  ) : (
                    <>
                      <Play className="w-5 h-5" />
                      Ejecutar Scraping
                    </>
                  )}
                </button>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
