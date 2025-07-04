﻿# subfinder.py
import os
import sys
import asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils.validator import DomainValidator, IPValidator
from src.utils.console import SubFinderConsole
from src.utils.telegram import TelegramBot
from src.sources.sources import get_sources

class SubFinder:
    def __init__(self, bot_token, output_file="subdomains.txt"):
        self.console = SubFinderConsole()
        self.bot = TelegramBot(bot_token, self)
        self.output_file = output_file
        self.completed = 0
        self.domains = []

    def _fetch_from_source(self, source, domain):
        try:
            found = source.fetch(domain)
            return DomainValidator.filter_valid_subdomains(found, domain)
        except Exception as e:
            self.console.print_error(f"Error in {source.name}: {str(e)}")
            return set()

    async def save_subdomains(self, subdomains, output_file, chat_id):
        try:
            if subdomains:
                os.makedirs(os.path.dirname(output_file) or '.', exist_ok=True)
                with open(output_file, "w", encoding="utf-8") as f:
                    f.write("\n".join(sorted(subdomains)) + "\n")
                self.console.print(f"Results saved to {output_file}")
                await self.bot.send_file(output_file, len(subdomains), chat_id)
                try:
                    os.remove(output_file)
                    self.console.print(f"Deleted local file: {output_file}")
                except Exception as e:
                    self.console.print_error(f"Error deleting file {output_file}: {str(e)}")
                    await self.bot.send_message(f"Error deleting file {output_file}: {str(e)}", chat_id)
            else:
                self.console.print_error("No subdomains found, no file saved.")
                await self.bot.send_message("No subdomains found, no file saved.", chat_id)
        except Exception as e:
            self.console.print_error(f"Error saving subdomains: {str(e)}")
            await self.bot.send_message(f"Error saving subdomains: {str(e)}", chat_id)

    async def process_domain(self, domain, sources, cancel_event):
        if cancel_event.is_set():
            self.console.print(f"Scan cancelled for domain: {domain}")
            return set()

        if not DomainValidator.is_valid_domain(domain):
            self.console.print_error(f"Invalid domain: {domain}")
            return set()

        self.console.print_domain_start(domain)
        
        try:
            with ThreadPoolExecutor(max_workers=6) as executor:
                futures = [executor.submit(self._fetch_from_source, source, domain) for source in sources]
                results = [f.result() for f in as_completed(futures)]
        except Exception as e:
            self.console.print_error(f"Error fetching subdomains for {domain}: {str(e)}")
            return set()

        subdomains = set().union(*results) if results else set()
        self.console.update_domain_stats(domain, len(subdomains))
        self.console.print_domain_complete(domain, len(subdomains))

        return subdomains

    async def run_async(self, input_data, is_file=False, cancel_event=None, bot=None, chat_id=None):
        try:
            sources = get_sources()
            self.domains = []  # Reset domains
            self.completed = 0  # Reset completed

            if is_file:
                try:
                    with open(input_data, 'r', encoding='utf-8') as f:
                        self.domains = [d.strip() for d in f if d.strip()]
                    self.output_file = "subdomains.txt"
                except Exception as e:
                    self.console.print_error(f"Error reading file {input_data}: {str(e)}")
                    await bot.send_message(f"Error reading input file: {str(e)}", chat_id)
                    return
            else:
                if isinstance(input_data, list):
                    self.domains = [d for d in input_data if DomainValidator.is_valid_domain(d) or IPValidator.is_valid_ip_cidr(d)]
                    self.output_file = "subdomains.txt"
                else:
                    if DomainValidator.is_valid_domain(input_data) or IPValidator.is_valid_ip_cidr(input_data):
                        self.domains = [input_data]
                        self.output_file = "subdomains.txt"
                    else:
                        self.console.print_error(f"Invalid input: {input_data}")
                        await bot.send_message(f"Invalid input: {input_data}", chat_id)
                        return

            if not self.domains:
                self.console.print_error("No valid domains provided")
                await bot.send_message("No valid domains provided", chat_id)
                return

            total = len(self.domains)
            all_subdomains = set()

            if os.path.exists(self.output_file):
                try:
                    os.remove(self.output_file)
                except Exception as e:
                    self.console.print_error(f"Error clearing output file {self.output_file}: {str(e)}")
                    await bot.send_message(f"Error clearing output file {self.output_file}: {str(e)}", chat_id)

            max_concurrent = 3
            for i in range(0, len(self.domains), max_concurrent):
                if cancel_event and cancel_event.is_set():
                    self.console.print("Scan cancelled")
                    await bot.send_message("Scan cancelled", chat_id)
                    break
                batch = self.domains[i:i + max_concurrent]
                tasks = [self.process_domain(domain, sources, cancel_event) for domain in batch]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                self.completed += len([r for r in results if isinstance(r, set)])
                await bot.update_progress(self.completed / total, chat_id)
                for result in results:
                    if isinstance(result, set):
                        all_subdomains.update(result)
                    else:
                        self.console.print_error(f"Error processing domain: {str(result)}")
                self.console.print_progress(self.completed, total)

            if cancel_event and cancel_event.is_set():
                return

            await self.save_subdomains(all_subdomains, self.output_file, chat_id)
            self.console.print_final_summary(self.output_file)
        except Exception as e:
            self.console.print_error(f"Error in run_async: {str(e)}")
            await bot.send_message(f"Error during scan: {str(e)}", chat_id)
        finally:
            self.domains = []
            self.completed = 0

def main():
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")

    if not bot_token:
        print("Error: TELEGRAM_BOT_TOKEN must be set as an environment variable")
        return

    try:
        subfinder = SubFinder(bot_token)
        subfinder.bot.run()
    except Exception as e:
        print(f"Error in main: {str(e)}")

if __name__ == "__main__":
    main()