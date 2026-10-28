"use client";
import { useEffect, useState } from "react";

export default function Home() {
	const [message, setMessage] = useState("Loading...");

	useEffect(() => {
		fetch("http://localhost:8000/")
			.then((res) => res.json())
			.then((data) => setMessage(data.message))
			.catch((err) => setMessage("Failed to connect to backend"));
	}, []);

	return (
		<main style={{ padding: "40px", fontFamily: "sans-serif" }}>
			<h1>hi my name is sampreet</h1>
			<p
				style={{
					background: "#eee",
					color: "#000",
					padding: "15px",
					borderRadius: "5px",
					marginTop: "20px",
				}}>
				Response: <strong style={{ color: "#000" }}>{message}</strong>
			</p>
		</main>
	);
}
