import { Agent } from "../../scratch/skawld-sdk/dist/sdk.js";
import { OpenAIChatCompletionsProvider } from "../../scratch/skawld-sdk/dist/providers/index.js";
import { InMemorySessionStore } from "../../scratch/skawld-sdk/dist/sessions/memory.js";

async function main() {
  const provider = new OpenAIChatCompletionsProvider({
    apiKey: process.env.GEMINI_API_KEY,
    baseURL: "https://generativelanguage.googleapis.com/v1beta/openai/",
  });

  console.log("Testing connection to Gemini OpenAI-compatible API...");

  try {
    const agent = new Agent({
      provider,
      model: "gemini-2.5-flash",
      sessionStore: new InMemorySessionStore(),
      permissions: { mode: "yolo" },
    });

    const session = await agent.session();
    console.log("Session started successfully!");

    for await (const event of session.run("Respond with exactly the word 'SUCCESS' if you read this.")) {
      console.log(`Event type: ${event.type}`);
      if (event.type === "assistant") {
        console.log("Assistant content:", JSON.stringify(event.message.content));
      }
      if (event.type === "error") {
        console.error("Agent error detail:", event.error);
      }
      if (event.type === "result") {
        console.log("Result content:", event);
        break;
      }
    }

    await agent.close();
  } catch (error) {
    console.error("Connection test failed:", error);
  }
}

main();
