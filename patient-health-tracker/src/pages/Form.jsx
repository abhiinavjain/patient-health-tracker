import React, { useState } from "react";

const Form = () => {
  const [formData, setFormData] = useState({
    name: "",
    email: "",
    phone: "",
    appointmentDate: ""
  });
  const [resultMessage, setResultMessage] = useState("");
  const [resultColor, setResultColor] = useState("text-gray-400");

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value
    });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setResultMessage("Please wait...");
    setResultColor("text-gray-400");

    const response = await fetch("https://api.web3forms.com/submit", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json"
      },
      body: JSON.stringify({
        ...formData,
        access_key: import.meta.env.VITE_ACCESS_KEY,
        subject: "Appointment scheduled from Well Path"
      })
    });

    const json = await response.json();

    if (response.ok) {
      setResultMessage(json.message);
      setResultColor("text-blue-500");
    } else {
      setResultMessage(json.message || "Something went wrong!");
      setResultColor("text-red-500");
    }

    setFormData({ name: "", email: "", phone: "", appointmentDate: "" });
    setTimeout(() => setResultMessage(""), 5000);
  };

  return (
    <div className=" flex items-center justify-center">
      <div className="container mx-auto">
        <div className="max-w-md mx-auto my-10 p-6 rounded-lg shadow-md">
          <h1 className="text-3xl font-bold text-center mb-6">Book an Appointment</h1>
          <p className="text-center mb-6 text-gray-600">
            Fill up the form below to schedule an appointment with us.
          </p>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label htmlFor="name" className="block mb-2 font-semibold">
                Full Name:
              </label>
              <input
                type="text"
                name="name"
                id="name"
                placeholder="Enter your name"
                value={formData.name}
                onChange={handleChange}
                required
                className="w-full border border-gray-300 p-2 rounded-lg"
              />
            </div>
            <div>
              <label htmlFor="email" className="block mb-2 font-semibold">
                Email Address:
              </label>
              <input
                type="email"
                name="email"
                id="email"
                placeholder="Enter your email"
                value={formData.email}
                onChange={handleChange}
                required
                className="w-full border border-gray-300 p-2 rounded-lg"
              />
            </div>
            <div>
              <label htmlFor="phone" className="block mb-2 font-semibold">
                Phone Number:
              </label>
              <input
                type="text"
                name="phone"
                id="phone"
                placeholder="Enter your phone number"
                value={formData.phone}
                onChange={handleChange}
                required
                className="w-full border border-gray-300 p-2 rounded-lg"
              />
            </div>
            <div>
              <label htmlFor="appointmentDate" className="block mb-2 font-semibold">
                Appointment Date & Time:
              </label>
              <input
                type="datetime-local"
                name="appointmentDate"
                id="appointmentDate"
                value={formData.appointmentDate}
                onChange={handleChange}
                required
                className="w-full border border-gray-300 p-2 rounded-lg"
              />
            </div>
            <button
              type="submit"
              className="w-full text-white font-semibold py-2 px-4 rounded-lg"
            >
              Schedule Appointment
            </button>
            {resultMessage && (
              <p className={`text-center mt-4 ${resultColor}`}>
                {resultMessage}
              </p>
            )}
          </form>
        </div>
      </div>
    </div>
  );
};

export default Form;


