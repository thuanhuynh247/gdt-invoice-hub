import { Agent } from "../../scratch/skawld-sdk/src/sdk.js";
import { OpenAIChatCompletionsProvider } from "../../scratch/skawld-sdk/src/providers/index.js";
import { InMemorySessionStore } from "../../scratch/skawld-sdk/src/sessions/memory.js";

async function main() {
  const provider = new OpenAIChatCompletionsProvider({
    apiKey: process.env.GEMINI_API_KEY,
    baseURL: "https://generativelanguage.googleapis.com/v1beta/openai/",
  });

  console.log("Testing connection to Gemini OpenAI-compatible API...");

  try {
    const agent = new Agent({
      provider,
      model: "gemini-1.5-flash",
      sessionStore: new InMemorySessionStore(),
      permissions: { mode: "yolo" },
    });

    const session = await agent.session();
    console.log("Session started successfully!");

    for await (const event of session.run("Respond with exactly the word 'SUCCESS' if you read this.")) {
      if (event.type === "assistant") {
        for (const block of event.message.content) {
          if (block.type === "text") {
            process.stdout.write(block.text);
          }
        }
      }
      if (event.type === "result") {
        process.stdout.write("\n");
        break;
      }
    }

    await agent.close();
  } catch (error) {
    console.error("Connection test failed:", error);
  }
}

main();
