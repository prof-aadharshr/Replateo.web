import { useEffect, useState } from "react";
import { useAuth } from "../context/AuthContext";
import { useToast } from "../context/ToastContext";
import {
  collection,
  query,
  where,
  orderBy,
  onSnapshot,
  updateDoc,
  doc,
  addDoc,
  serverTimestamp,
} from "firebase/firestore";
import { db } from "../firebase";

export default function Dashboard({ openAuthModal }) {
  const { user } = useAuth();
  const { addToast } = useToast();

  const [listings, setListings] = useState([]);
  const [claimedListings, setClaimedListings] = useState([]);
  const [stats, setStats] = useState({
    donations: 0,
    claimed: 0,
    pending: 0,
  });

  // 🚫 Not logged in
  if (!user) {
    return (
      <section className="page-section">
        <div className="page-container text-center">
          <h2 className="text-3xl font-bold text-orange-800 mb-4">
            Access Required
          </h2>
          <button
            onClick={openAuthModal}
            className="px-6 py-3 bg-orange-600 text-white rounded-xl"
          >
            Login / Register
          </button>
        </div>
      </section>
    );
  }

  // 🔹 USER DONATIONS (FIXED)
  useEffect(() => {
    const q = query(
      collection(db, "food_listings"),
      where("userId", "==", user.uid), // ✅ FIXED
      orderBy("createdAt", "desc")
    );

    const unsub = onSnapshot(q, (snap) => {
      let donations = 0;
      let pending = 0;
      let claimed = 0;

      const arr = snap.docs.map((d) => {
        const data = { id: d.id, ...d.data() };

        if (data.type === "donation") donations++;
        if (data.status === "available") pending++;
        if (data.status === "claimed") claimed++;

        return data;
      });

      setListings(arr);
      setStats({ donations, pending, claimed });
    });

    return () => unsub();
  }, [user.uid]);

  // 🔹 ITEMS CLAIMED (NGO ONLY)
  useEffect(() => {
    if (user.role !== "ngo") return;

    const q = query(
      collection(db, "food_listings"),
      where("claimedBy", "==", user.uid),
      orderBy("claimedAt", "desc")
    );

    const unsub = onSnapshot(q, (snap) => {
      const arr = snap.docs.map((d) => ({
        id: d.id,
        ...d.data(),
      }));
      setClaimedListings(arr);
    });

    return () => unsub();
  }, [user]);

  return (
    <section className="page-section">
      <div className="page-container">

        {/* HEADER */}
        <h2 className="text-4xl font-bold text-orange-800 mb-10">
          Welcome, {user.displayName || user.email}
        </h2>

        {/* STATS */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-6 mb-14">
          <Stat label="Donations" value={stats.donations} />
          <Stat label="Claimed" value={stats.claimed} />
          <Stat label="Pending" value={stats.pending} />
        </div>

        {/* ITEMS CLAIMED – NGO ONLY */}
        {user.role === "ngo" && (
          <>
            <h3 className="text-2xl font-bold text-orange-800 mb-4">
              Items You Claimed
            </h3>

            {claimedListings.length === 0 ? (
              <p>No items claimed yet.</p>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-16">
                {claimedListings.map((item) => (
                  <Card key={item.id} item={item} />
                ))}
              </div>
            )}
          </>
        )}

        {/* USER LISTINGS */}
        <h3 className="text-2xl font-bold text-orange-800 mb-4">
          Your Listings
        </h3>

        {listings.length === 0 ? (
          <p>You haven’t posted anything yet.</p>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {listings.map((item) => (
              <div key={item.id} className="border rounded-xl p-5">
                <h4 className="font-bold">{item.title}</h4>
                <p className="text-sm">{item.notes}</p>

                <span className="text-sm font-semibold text-orange-700">
                  Status: {item.status}
                </span>
              </div>
            ))}
          </div>
        )}

      </div>
    </section>
  );
}

/* SMALL COMPONENTS */
function Stat({ label, value }) {
  return (
    <div className="bg-orange-50 p-6 rounded-xl text-center">
      <p className="text-sm text-orange-700">{label}</p>
      <p className="text-3xl font-bold text-orange-800">{value}</p>
    </div>
  );
}

function Card({ item }) {
  return (
    <div className="border rounded-xl p-5">
      <h4 className="font-bold">{item.title}</h4>
      <p className="text-sm">{item.notes}</p>
      <span className="text-green-700 font-semibold">Claimed</span>
    </div>
  );
}