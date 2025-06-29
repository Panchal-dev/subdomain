import os
import asyncio
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from src.utils.validator import DomainValidator, IPValidator
from src.utils.console import SubFinderConsole
from src.utils.telegram import TelegramBot
from src.sources.sources import get_sources

class SubFinder:
    def __init__(self, bot_token, chat_id, output_file="subdomains.txt"):
        self.console = SubFinderConsole()
        self.bot = TelegramBot(bot_token, chat_id, self)
        self.output_file = output_file
        self.completed = 0
        self.batch_size = 100  # Process 100 domains at a time

    def _fetch_from_source(self, source, domain, retries=3):
        for attempt in range(retries):
            try:
                found = source.fetch(domain)
                return DomainValidator.filter_valid_subdomains(found, domain)
            except Exception as e:
                if attempt == retries - 1:
                    self.console.print_error(f"Error in {source.name} for {domain}: {str(e)}")
                    return set()
                self.console.print(f"Retrying {source.name} for {domain} ({attempt + 1}/{retries})")
                asyncio.sleep(1)  # Brief delay before retry

    async def save_subdomains(self, subdomains, output_file):
        if subdomains:
            os.makedirs(os.path.dirname(output_file) or '.', exist_ok=True)
            with open(output_file, "a", encoding="utf-8") as f:
                f.write("\n".join(sorted(subdomains)) + "\n")
            self.console.print(f"Results saved to {output_file}")
            await self.bot.send_message(f"Subdomain enumeration complete. Results saved to {output_file}\nFound {len(subdomains)} subdomains.")
            await self.bot.send_file(output_file)
            try:
                os.remove(output_file)
                self.console.print(f"Deleted local file: {output_file}")
            except Exception as e:
                self.console.print_error(f"Error deleting file {output_file}: {str(e)}")
                await self.bot.send_message(f"Error deleting file {output_file}: {str(e)}")
        else:
            self.console.print_error("No subdomains found, no file saved.")
            await self.bot.send_message("No subdomains found, no file saved.")

    async def process_domain(self, domain, sources, total, cancel_event):
        if cancel_event.is_set():
            self.console.print(f"Scan cancelled for domain: {domain}")
            await self.bot.send_message(f"Scan cancelled for domain: {domain}")
            return set()

        if not DomainValidator.is_valid_domain(domain):
            self.console.print_error(f"Invalid domain: {domain}")
            await self.bot.send_message(f"Invalid domain: {domain}")
            self.completed += 1
            return set()

        self.console.print_domain_start(domain)
        self.console.print_progress(self.completed, total)
        
        with ThreadPoolExecutor(max_workers=3) as executor:  # Reduced workers
            futures = [executor.submit(self._fetch_from_source, source, domain) for source in sources]
            results = [f.result() for f in as_completed(futures)]

        subdomains = set().union(*results) if results else set()
        self.console.update_domain_stats(domain, len(subdomains))
        self.console.print_domain_complete(domain, len(subdomains))
        await self.save_subdomains(subdomains, self.output_file)

        self.completed += 1
        self.console.print_progress(self.completed, total)
        return subdomains

    async def run_async(self, input_data, is_file=False, cancel_event=None):
        sources = get_sources()
        domains = []

        if is_file:
            try:
                with open(input_data, 'r', encoding='utf-8') as f:
                    domains = [d.strip() for d in f if DomainValidator.is_valid_domain(d.strip())]
                self.output_file = f"{input_data.rsplit('.', 1)[0]}_subdomains.txt"
            except Exception as e:
                self.console.print_error(f"Error reading file {input_data}: {str(e)}")
                await self.bot.send_message(f"Error reading input file: {str(e)}")
                return
        else:
            if isinstance(input_data, list):
                domains = [d for d in input_data if DomainValidator.is_valid_domain(d) or IPValidator.is_valid_ip_cidr(d)]
                self.output_file = "subdomains.txt"
            else:
                if DomainValidator.is_valid_domain(input_data) or IPValidator.is_valid_ip_cidr(input_data):
                    domains = [input_data]
                    self.output_file = f"{input_data}_subdomains.txt"
                else:
                    self.console.print_error(f"Invalid input: {input_data}")
                    await self.bot.send_message(f"Invalid input: {input_data}")
                    return

        if not domains:
            self.console.print_error("No valid domains provided")
            await self.bot.send_message("No valid domains provided")
            return

        await self.bot.send_message(f"Starting subdomain enumeration for {len(domains)} domains")
        total = len(domains)
        all_subdomains = set()

        if os.path.exists(self.output_file):
            try:
                os.remove(self.output_file)
            except Exception as e:
                self.console.print_error(f"Error clearing output file {self.output_file}: {str(e)}")
                await self.bot.send_message(f"Error clearing output file {self.output_file}: {str(e)}")

        # Process domains in batches
        for i in range(0, len(domains), self.batch_size):
            if cancel_event and cancel_event.is_set():
                self.console.print("Scan cancelled")
                await self.bot.send_message("Scan cancelled")
                break
            batch = domains[i:i + self.batch_size]
            self.console.print(f"Processing batch {i//self.batch_size + 1} ({len(batch)} domains)")
            await self.bot.send_message(f"Processing batch {i//self.batch_size + 1} ({len(batch)} domains)")

            with ThreadPoolExecutor(max_workers=3) as executor:
                futures = [executor.submit(self.process_domain, domain, sources, total, cancel_event) for domain in batch]
                for future in as_completed(futures):
                    try:
                        result = await future.result()
                        all_subdomains.update(result)
                    except Exception as e:
                        self.console.print_error(f"Error processing domain: {str(e)}")
                        await self.bot.send_message(f"Error processing domain: {str(e)}")

        self.console.print_final_summary(self.output_file)
        await self.bot.send_message(f"Total: {len(all_subdomains)} subdomains found for {len(domains)} domains")

def main():
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    if not bot_token or not chat_id:
        print("Error: TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID must be set as environment variables")
        return

    subfinder = SubFinder(bot_token, chat_id)
    subfinder.bot.run()

if __name__ == "__main__":
    main()