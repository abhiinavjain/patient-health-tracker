import React from "react";
import { Link } from "react-router-dom"; // Assuming you're using react-router for navigation
import { BackgroundGradient } from "../components/ui/BackgroundGradient";
import { Cover } from "../components/ui/cover";

const Home = () => {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center p-8 text-gray-800">
      <header className="text-center mb-12">
  <h1 className="text-5xl font-extrabold mb-4 text-grey-600">Welcome to <Cover>Well Path </Cover></h1>
  <p className="text-xl font-semibold text-gray-700">
    Your journey to wellness starts here—track your health history effortlessly!
  </p>
</header>
<p className="text-center text-lg mb-12 max-w-xl mx-auto text-gray-600">
  Tired of juggling your doctor consultations? With Well Path,
  you have a trusted companion by your side, capturing every detail of your health journey.
   As you consult with your doctors, your records are automatically updated, ensuring you have everything at your fingertips. 
   Take control of your health story and embrace a brighter, healthier future!
</p>


      {/* Call to Action Button */}
      <div className="flex justify-center mt-8">
        <Link to="/add-patient">
          <button className="px-6 py-3 border border-gray-800 text-white-800 font-semibold rounded-full bg-grey  shadow-md">
            Get Started
          </button>
        </Link>
      </div>

      {/* Features Section */}
      <section className="mt-12 space-y-6">
      <BackgroundGradient  className="cardb rounded-[22px] sm:p-6 bg-white">
        <div className="max-w-3xl mx-auto grid gap-8 md:grid-cols-2 lg:grid-cols-3">
          <div className="border border-gray-300 rounded-lg p-6 hover:bg-gray-50 transition duration-300 shadow-sm">
            <h2 className="text-xl font-bold mb-2">Track Health History</h2>
            <p>Seamlessly record and access your medical history for easy tracking.</p>
          </div>
          <div className="border border-gray-300 rounded-lg p-6 hover:bg-gray-50 transition duration-300 shadow-sm">
            <h2 className="text-xl font-bold mb-2">Consultation Updates</h2>
            <p>Keep updated with your latest health records from consultations.</p>
          </div>
          <div className="border border-gray-300 rounded-lg p-6 hover:bg-gray-50 transition duration-300 shadow-sm">
            <h2 className="text-xl font-bold mb-2">Secure Data Storage</h2>
            <p>Your health data is encrypted and stored securely for your peace of mind.</p>
          </div>
        </div>
        </BackgroundGradient>
      </section>


      {/* Footer */}
      <footer className="mt-16 text-center">
        <p className="text-sm text-gray-500">&copy; 2024 Well Path. All rights reserved.</p>
      </footer>
    </div>
  );
};

export default Home;
