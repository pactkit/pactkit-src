import axios from "axios";

export function Dashboard() {
  const load = async () => {
    const res = await axios.get("/api/v1/dashboard");
    return res.data;
  };

  const update = async (data: any) => {
    await axios.post("/api/v1/dashboard/update", data);
  };

  return <div />;
}
