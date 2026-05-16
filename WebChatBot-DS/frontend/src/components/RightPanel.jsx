import { Heart, Droplets, Pill, AlertCircle } from "lucide-react";

export default function RightPanel({
  vitals = {
    restingHR: 72,
    bpm: "BPM",
    bloodPressure: "128/84",
  },
  profile = {
    age: 42,
    gender: "Male",
    weight: 185,
    height: "5'10\"",
    bloodType: "A+",
    bloodTypeSubtext: "Positive",
  },
  allergies = ["PENICILLIN", "LATEX"],
  medications = [
    { name: "Lisinopril", dosage: "10mg", frequency: "Daily", badge: "TODAY" },
    {
      name: "Metformin",
      dosage: "Extended Release",
      frequency: "Twice Daily",
      badge: "DUE IN 21",
    },
  ],
}) {
  return (
    <div className="w-48 h-screen bg-white border-l border-slate-200 overflow-y-auto">
      {/* Quick Stats */}
      <div className="p-6 border-b border-slate-200">
        <h3 className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-4">
          Quick Stats
        </h3>

        {/* HR Card */}
        <div className="bg-gradient-to-br from-blue-50 to-blue-100/50 rounded-2xl p-3 mb-4 flex gap-4 items-center">
          <div className="bg-white rounded-full p-2 shadow-sm flex items-center justify-center">
            <Heart size={20} className="text-red-500" />
          </div>
          <div className="flex-1">
            <p className="text-xs font-medium text-slate-600 leading-tight">
              Resting HR
            </p>
            <p className="text-lg font-bold text-slate-900">
              {vitals.restingHR}
            </p>
            <p className="text-xs text-slate-600">{vitals.bpm}</p>
          </div>
        </div>

        {/* Blood Pressure Card */}
        <div className="bg-gradient-to-br from-emerald-50 to-emerald-100/50 rounded-2xl p-3 flex gap-4 items-center">
          <div className="bg-white rounded-full p-2 shadow-sm flex items-center justify-center">
            <Droplets size={20} className="text-emerald-600" />
          </div>
          <div className="flex-1">
            <p className="text-xs font-medium text-slate-600 leading-tight">
              Blood Pressure
            </p>
            <p className="text-lg font-bold text-slate-900">
              {vitals.bloodPressure}
            </p>
            <p className="text-xs text-slate-600">mmHg</p>
          </div>
        </div>
      </div>

      {/* Current Health Profile */}
      <div className="p-6 border-b border-slate-200">
        <h3 className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-4">
          Current Health Profile
        </h3>

        <div className="space-y-3">
          <div>
            <p className="text-xs text-slate-500 font-medium mb-1">
              Age / Gender
            </p>
            <p className="text-sm font-semibold text-slate-900">
              {profile.age} / {profile.gender}
            </p>
          </div>

          <div>
            <p className="text-xs text-slate-500 font-medium mb-1">Weight</p>
            <p className="text-sm font-semibold text-slate-900">
              {profile.weight} lbs
            </p>
          </div>

          <div>
            <p className="text-xs text-slate-500 font-medium mb-1">
              Blood Type
            </p>
            <p className="text-sm font-semibold text-slate-900">
              {profile.bloodType}{" "}
              <span className="text-xs text-slate-600">
                {profile.bloodTypeSubtext}
              </span>
            </p>
          </div>
        </div>
      </div>

      {/* Allergies */}
      {allergies.length > 0 && (
        <div className="p-6 border-b border-slate-200">
          <h3 className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-3">
            Allergies
          </h3>
          <div className="space-y-2">
            {allergies.map((allergy) => (
              <div
                key={allergy}
                className="bg-red-50 rounded-lg px-3 py-2 flex items-center gap-2"
              >
                <AlertCircle size={14} className="text-red-600 flex-shrink-0" />
                <span className="text-xs font-semibold text-red-700">
                  {allergy}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Active Medications */}
      {medications.length > 0 && (
        <div className="p-6">
          <h3 className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-4">
            Active Medications
          </h3>

          <div className="space-y-3">
            {medications.map((med, idx) => (
              <div
                key={idx}
                className="bg-slate-50 rounded-lg p-3 border border-slate-200 hover:border-slate-300 transition"
              >
                <div className="flex items-start gap-2 mb-2">
                  <Pill
                    size={14}
                    className="text-blue-600 mt-1 flex-shrink-0"
                  />
                  <div className="flex-1 min-w-0">
                    <p className="text-xs font-bold text-slate-900">
                      {med.name}
                    </p>
                    <p className="text-xs text-slate-600 truncate">
                      {med.dosage}
                    </p>
                  </div>
                  {med.badge && (
                    <span className="text-xs font-bold text-green-700 bg-green-100 px-2 py-0.5 rounded whitespace-nowrap flex-shrink-0">
                      {med.badge}
                    </span>
                  )}
                </div>
                <p className="text-xs text-slate-500">{med.frequency}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
