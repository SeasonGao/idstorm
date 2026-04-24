import axios from "axios";
import { API_BASE } from "../utils/constants";

const apiClient = axios.create({
  baseURL: API_BASE,
  timeout: 120000,
  headers: {
    "Content-Type": "application/json",
  },
});

export default apiClient;
